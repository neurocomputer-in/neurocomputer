package com.termux.terminal;

import android.annotation.SuppressLint;
import android.os.Handler;
import android.os.Message;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;

import java.io.File;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/**
 * A terminal session, consisting of a process coupled to a terminal interface.
 * <p>
 * The subprocess will be executed by the constructor, and when the size is made known by a call to
 * {@link #updateSize(int, int, int, int)} terminal emulation will begin and threads will be spawned to handle the subprocess I/O.
 * All terminal emulation and callback methods will be performed on the main thread.
 * <p>
 * The child process may be exited forcefully by using the {@link #finishIfRunning()} method.
 * <p>
 * NOTE: The terminal session may outlive the EmulatorView, so be careful with callbacks!
 */
public class TerminalSession extends TerminalOutput {

    /** Bridge for "remote PTY" mode: keystroke bytes the user types are forwarded
     *  to the implementer (e.g. WebSocket) instead of a local pty fd. */
    public interface RemoteOutputHandler {
        void onTerminalOutput(byte[] data, int offset, int count);
    }

    private static final int MSG_NEW_INPUT = 1;
    private static final int MSG_PROCESS_EXITED = 4;
    private static final int MSG_REMOTE_INPUT = 5;

    private boolean mRemote;
    private RemoteOutputHandler mRemoteHandler;

    public final String mHandle = UUID.randomUUID().toString();

    TerminalEmulator mEmulator;

    /**
     * A queue written to from a separate thread when the process outputs, and read by main thread to process by
     * terminal emulator.
     */
    final ByteQueue mProcessToTerminalIOQueue = new ByteQueue(64 * 1024);
    /**
     * A queue written to from the main thread due to user interaction, and read by another thread which forwards by
     * writing to the {@link #mTerminalFileDescriptor}.
     */
    final ByteQueue mTerminalToProcessIOQueue = new ByteQueue(4096);
    /** Buffer to write translate code points into utf8 before writing to mTerminalToProcessIOQueue */
    private final byte[] mUtf8InputBuffer = new byte[5];

    /** Callback which gets notified when a session finishes or changes title. */
    TerminalSessionClient mClient;

    /** The pid of the shell process. 0 if not started and -1 if finished running. */
    int mShellPid;

    /** The exit status of the shell process. Only valid if ${@link #mShellPid} is -1. */
    int mShellExitStatus;

    /**
     * The file descriptor referencing the master half of a pseudo-terminal pair, resulting from calling
     * {@link JNI#createSubprocess(String, String, String[], String[], int[], int, int, int, int)}.
     */
    private int mTerminalFileDescriptor;

    /** Set by the application for user identification of session, not by terminal. */
    public String mSessionName;

    final Handler mMainThreadHandler = new MainThreadHandler();

    private final String mShellPath;
    private final String mCwd;
    private final String[] mArgs;
    private final String[] mEnv;
    private final Integer mTranscriptRows;


    private static final String LOG_TAG = "TerminalSession";

    public TerminalSession(String shellPath, String cwd, String[] args, String[] env, Integer transcriptRows, TerminalSessionClient client) {
        this.mShellPath = shellPath;
        this.mCwd = cwd;
        this.mArgs = args;
        this.mEnv = env;
        this.mTranscriptRows = transcriptRows;
        this.mClient = client;
    }

    /** Construct a session backed by a remote PTY. JNI/local-process paths stay
     *  inert; bytes received from the remote side must be fed via {@link #appendRemoteOutput}.
     *  Bytes the user types are delivered to {@code remoteHandler}. */
    public TerminalSession(RemoteOutputHandler remoteHandler, Integer transcriptRows, TerminalSessionClient client) {
        this.mShellPath = null;
        this.mCwd = null;
        this.mArgs = null;
        this.mEnv = null;
        this.mTranscriptRows = transcriptRows;
        this.mClient = client;
        this.mRemote = true;
        this.mRemoteHandler = remoteHandler;
        this.mShellPid = 1; // pretend running so write() / size paths stay active
    }

    /**
     * @param client The {@link TerminalSessionClient} interface implementation to allow
     *               for communication between {@link TerminalSession} and its client.
     */
    public void updateTerminalSessionClient(TerminalSessionClient client) {
        mClient = client;

        if (mEmulator != null)
            mEmulator.updateTerminalSessionClient(client);
    }

    /** Inform the attached pty of the new size and reflow or initialize the emulator. */
    public void updateSize(int columns, int rows, int cellWidthPixels, int cellHeightPixels) {
        if (mEmulator == null) {
            initializeEmulator(columns, rows, cellWidthPixels, cellHeightPixels);
        } else {
            if (mRemote) {
                onRemoteResize(columns, rows);
            } else {
                Logger.logWarn(mClient, LOG_TAG, "JNI.setPtyWindowSize unavailable (vendored without native lib)");
            }
            mEmulator.resize(columns, rows, cellWidthPixels, cellHeightPixels);
        }
    }

    /** Notify the caller that the remote pty should resize. Override or pass via
     *  client to forward to the WebSocket. */
    public void onRemoteResize(int columns, int rows) {
        // Default no-op; intended for the remote bridge to listen by overriding.
    }

    /** The terminal title as set through escape sequences or null if none set. */
    public String getTitle() {
        return (mEmulator == null) ? null : mEmulator.getTitle();
    }

    /**
     * Set the terminal emulator's window size and start terminal emulation.
     *
     * @param columns The number of columns in the terminal window.
     * @param rows    The number of rows in the terminal window.
     */
    public void initializeEmulator(int columns, int rows, int cellWidthPixels, int cellHeightPixels) {
        mEmulator = new TerminalEmulator(this, columns, rows, cellWidthPixels, cellHeightPixels, mTranscriptRows, mClient);
        if (mRemote) {
            // Remote mode: emulator runs against a WebSocket-backed pty. No local
            // process, no JNI, no reader/writer/waiter threads.
            mClient.setTerminalShellPid(this, mShellPid);
            onRemoteResize(columns, rows);
            return;
        }

        int[] processId = new int[1];
        mTerminalFileDescriptor = -1;
        // Native subprocess support stripped (JNI removed). Local-pty mode unavailable.
        throw new UnsupportedOperationException(
            "Local pty mode unavailable in this vendored build — use the remote constructor.");
    }

    /** Feed bytes received from the remote pty into the emulator. Safe to call
     *  from any thread — work is hopped to the main thread before touching
     *  the emulator (which is single-threaded). */
    public void appendRemoteOutput(byte[] data, int length) {
        if (!mRemote) return;
        if (!mProcessToTerminalIOQueue.write(data, 0, length)) return;
        mMainThreadHandler.sendEmptyMessage(MSG_NEW_INPUT);
    }

    /** Write data to the shell process (or remote pty in remote mode). */
    @Override
    public void write(byte[] data, int offset, int count) {
        if (mRemote) {
            if (mRemoteHandler != null) mRemoteHandler.onTerminalOutput(data, offset, count);
            return;
        }
        if (mShellPid > 0) mTerminalToProcessIOQueue.write(data, offset, count);
    }

    /** Write the Unicode code point to the terminal encoded in UTF-8. */
    public void writeCodePoint(boolean prependEscape, int codePoint) {
        if (codePoint > 1114111 || (codePoint >= 0xD800 && codePoint <= 0xDFFF)) {
            // 1114111 (= 2**16 + 1024**2 - 1) is the highest code point, [0xD800,0xDFFF] is the surrogate range.
            throw new IllegalArgumentException("Invalid code point: " + codePoint);
        }

        int bufferPosition = 0;
        if (prependEscape) mUtf8InputBuffer[bufferPosition++] = 27;

        if (codePoint <= /* 7 bits */0b1111111) {
            mUtf8InputBuffer[bufferPosition++] = (byte) codePoint;
        } else if (codePoint <= /* 11 bits */0b11111111111) {
            /* 110xxxxx leading byte with leading 5 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b11000000 | (codePoint >> 6));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | (codePoint & 0b111111));
        } else if (codePoint <= /* 16 bits */0b1111111111111111) {
            /* 1110xxxx leading byte with leading 4 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b11100000 | (codePoint >> 12));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | ((codePoint >> 6) & 0b111111));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | (codePoint & 0b111111));
        } else { /* We have checked codePoint <= 1114111 above, so we have max 21 bits = 0b111111111111111111111 */
            /* 11110xxx leading byte with leading 3 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b11110000 | (codePoint >> 18));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | ((codePoint >> 12) & 0b111111));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | ((codePoint >> 6) & 0b111111));
            /* 10xxxxxx continuation byte with following 6 bits */
            mUtf8InputBuffer[bufferPosition++] = (byte) (0b10000000 | (codePoint & 0b111111));
        }
        write(mUtf8InputBuffer, 0, bufferPosition);
    }

    public TerminalEmulator getEmulator() {
        return mEmulator;
    }

    /** Notify the {@link #mClient} that the screen has changed. */
    protected void notifyScreenUpdate() {
        mClient.onTextChanged(this);
    }

    /** Reset state for terminal emulator state. */
    public void reset() {
        mEmulator.reset();
        notifyScreenUpdate();
    }

    /** Finish this terminal session. In remote mode, just marks not-running and
     *  lets the parent close the WS. */
    public void finishIfRunning() {
        if (mRemote) {
            cleanupResources(0);
            return;
        }
        if (isRunning()) {
            try {
                Os.kill(mShellPid, OsConstants.SIGKILL);
            } catch (ErrnoException e) {
                Logger.logWarn(mClient, LOG_TAG, "Failed sending SIGKILL: " + e.getMessage());
            }
        }
    }

    /** Cleanup resources when the process exits. */
    void cleanupResources(int exitStatus) {
        synchronized (this) {
            mShellPid = -1;
            mShellExitStatus = exitStatus;
        }

        // Stop the reader and writer threads, and close the I/O streams
        mTerminalToProcessIOQueue.close();
        mProcessToTerminalIOQueue.close();
        // No JNI.close() — vendored without native lib. In local mode the FD is
        // never opened (initializeEmulator throws), so nothing to close.
    }

    @Override
    public void titleChanged(String oldTitle, String newTitle) {
        mClient.onTitleChanged(this);
    }

    public synchronized boolean isRunning() {
        return mShellPid != -1;
    }

    /** Only valid if not {@link #isRunning()}. */
    public synchronized int getExitStatus() {
        return mShellExitStatus;
    }

    @Override
    public void onCopyTextToClipboard(String text) {
        mClient.onCopyTextToClipboard(this, text);
    }

    @Override
    public void onPasteTextFromClipboard() {
        mClient.onPasteTextFromClipboard(this);
    }

    @Override
    public void onBell() {
        mClient.onBell(this);
    }

    @Override
    public void onColorsChanged() {
        mClient.onColorsChanged(this);
    }

    public int getPid() {
        return mShellPid;
    }

    /** Returns the shell's working directory or null if it was unavailable. */
    public String getCwd() {
        if (mShellPid < 1) {
            return null;
        }
        try {
            final String cwdSymlink = String.format("/proc/%s/cwd/", mShellPid);
            String outputPath = new File(cwdSymlink).getCanonicalPath();
            String outputPathWithTrailingSlash = outputPath;
            if (!outputPath.endsWith("/")) {
                outputPathWithTrailingSlash += '/';
            }
            if (!cwdSymlink.equals(outputPathWithTrailingSlash)) {
                return outputPath;
            }
        } catch (IOException | SecurityException e) {
            Logger.logStackTraceWithMessage(mClient, LOG_TAG, "Error getting current directory", e);
        }
        return null;
    }

    private static FileDescriptor wrapFileDescriptor(int fileDescriptor, TerminalSessionClient client) {
        FileDescriptor result = new FileDescriptor();
        try {
            Field descriptorField;
            try {
                descriptorField = FileDescriptor.class.getDeclaredField("descriptor");
            } catch (NoSuchFieldException e) {
                // For desktop java:
                descriptorField = FileDescriptor.class.getDeclaredField("fd");
            }
            descriptorField.setAccessible(true);
            descriptorField.set(result, fileDescriptor);
        } catch (NoSuchFieldException | IllegalAccessException | IllegalArgumentException e) {
            Logger.logStackTraceWithMessage(client, LOG_TAG, "Error accessing FileDescriptor#descriptor private field", e);
            System.exit(1);
        }
        return result;
    }

    @SuppressLint("HandlerLeak")
    class MainThreadHandler extends Handler {

        final byte[] mReceiveBuffer = new byte[64 * 1024];

        @Override
        public void handleMessage(Message msg) {
            int bytesRead = mProcessToTerminalIOQueue.read(mReceiveBuffer, false);
            if (bytesRead > 0) {
                mEmulator.append(mReceiveBuffer, bytesRead);
                notifyScreenUpdate();
            }

            if (msg.what == MSG_PROCESS_EXITED) {
                int exitCode = (Integer) msg.obj;
                cleanupResources(exitCode);

                String exitDescription = "\r\n[Process completed";
                if (exitCode > 0) {
                    // Non-zero process exit.
                    exitDescription += " (code " + exitCode + ")";
                } else if (exitCode < 0) {
                    // Negated signal.
                    exitDescription += " (signal " + (-exitCode) + ")";
                }
                exitDescription += " - press Enter]";

                byte[] bytesToWrite = exitDescription.getBytes(StandardCharsets.UTF_8);
                mEmulator.append(bytesToWrite, bytesToWrite.length);
                notifyScreenUpdate();

                mClient.onSessionFinished(TerminalSession.this);
            }
        }

    }

}
