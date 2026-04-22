package com.neurocomputer.neuromobile.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.*
import androidx.compose.ui.text.font.*
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.neurocomputer.neuromobile.ui.theme.NeuroColors
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.commonmark.Extension
import org.commonmark.ext.gfm.strikethrough.Strikethrough
import org.commonmark.ext.gfm.strikethrough.StrikethroughExtension
import org.commonmark.ext.gfm.tables.*
import org.commonmark.node.BlockQuote
import org.commonmark.node.BulletList
import org.commonmark.node.Code
import org.commonmark.node.Emphasis
import org.commonmark.node.FencedCodeBlock
import org.commonmark.node.HardLineBreak
import org.commonmark.node.Heading
import org.commonmark.node.HtmlBlock
import org.commonmark.node.HtmlInline
import org.commonmark.node.Image
import org.commonmark.node.IndentedCodeBlock
import org.commonmark.node.Link
import org.commonmark.node.ListItem
import org.commonmark.node.Node
import org.commonmark.node.OrderedList
import org.commonmark.node.SoftLineBreak
import org.commonmark.node.StrongEmphasis
import org.commonmark.node.ThematicBreak
import org.commonmark.parser.Parser

/**
 * Renders markdown text for AI messages using CommonMark parsing.
 */
@Composable
fun MarkdownText(
    markdown: String,
    modifier: Modifier = Modifier
) {
    val extensions: List<Extension> = remember {
        listOf(TablesExtension.create(), StrikethroughExtension.create())
    }
    val parser = remember(extensions) {
        Parser.builder().extensions(extensions).build()
    }
    val document = remember(markdown) {
        parser.parse(markdown)
    }

    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        var node = document.firstChild
        while (node != null) {
            RenderBlock(node)
            node = node.next
        }
    }
}

// ─── Block-level rendering ───────────────────────────────────────────

@Composable
private fun RenderBlock(node: Node) {
    when (node) {
        is Heading -> RenderHeading(node)
        is org.commonmark.node.Paragraph -> RenderParagraph(node)
        is FencedCodeBlock -> RenderCodeBlock(node.literal ?: "", node.info?.takeIf { it.isNotBlank() })
        is IndentedCodeBlock -> RenderCodeBlock(node.literal ?: "", null)
        is BlockQuote -> RenderBlockquote(node)
        is BulletList -> RenderBulletList(node)
        is OrderedList -> RenderOrderedList(node)
        is ThematicBreak -> RenderHorizontalRule()
        is TableBlock -> RenderTable(node)
        is HtmlBlock -> RenderParagraphText(node.literal ?: "")
        else -> {
            // Fallback: try to render inline content
            val text = collectText(node)
            if (text.isNotBlank()) {
                RenderParagraphText(text)
            }
        }
    }
}

@Composable
private fun RenderHeading(node: Heading) {
    val (fontSize, fontWeight) = when (node.level) {
        1 -> 22.sp to FontWeight.Bold
        2 -> 19.sp to FontWeight.Bold
        3 -> 17.sp to FontWeight.SemiBold
        4 -> 16.sp to FontWeight.SemiBold
        5 -> 15.sp to FontWeight.Medium
        else -> 15.sp to FontWeight.Medium
    }
    val annotated = buildInlineAnnotatedString(node)
    Text(
        text = annotated,
        color = NeuroColors.TextPrimary,
        fontSize = fontSize,
        fontWeight = fontWeight,
        lineHeight = fontSize * 1.3f,
        modifier = Modifier.padding(top = 4.dp, bottom = 2.dp)
    )
}

@Composable
private fun RenderParagraph(node: org.commonmark.node.Paragraph) {
    val context = LocalContext.current
    val annotated = buildInlineAnnotatedString(node)
    ClickableText(
        text = annotated,
        style = TextStyle(
            color = NeuroColors.TextSecondary,
            fontSize = 15.sp,
            lineHeight = 22.sp
        ),
        onClick = { offset ->
            annotated.getStringAnnotations("URL", offset, offset).firstOrNull()?.let { annotation ->
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(annotation.item))
                context.startActivity(intent)
            }
        }
    )
}

@Composable
private fun RenderParagraphText(text: String) {
    Text(
        text = text,
        color = NeuroColors.TextSecondary,
        fontSize = 15.sp,
        lineHeight = 22.sp
    )
}

// ─── Code blocks ─────────────────────────────────────────────────────

@Composable
private fun RenderCodeBlock(code: String, language: String?) {
    val trimmedCode = code.trimEnd('\n')
    val clipboardManager = LocalClipboardManager.current
    var copied by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(NeuroColors.CodeBlockBackground)
            .border(0.5.dp, NeuroColors.CodeBlockBorder, RoundedCornerShape(12.dp))
    ) {
        // Header: language label + copy button
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(NeuroColors.CodeBlockHeaderBackground)
                .padding(horizontal = 12.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = language?.uppercase() ?: "CODE",
                color = NeuroColors.TextDim,
                fontSize = 11.sp,
                fontWeight = FontWeight.Medium,
                letterSpacing = 0.5.sp
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .clip(RoundedCornerShape(6.dp))
                    .clickable {
                        clipboardManager.setText(AnnotatedString(trimmedCode))
                        copied = true
                        scope.launch {
                            delay(2000)
                            copied = false
                        }
                    }
                    .padding(horizontal = 8.dp, vertical = 4.dp)
            ) {
                Icon(
                    imageVector = if (copied) Icons.Default.Check else Icons.Default.ContentCopy,
                    contentDescription = if (copied) "Copied" else "Copy code",
                    tint = if (copied) NeuroColors.Success else NeuroColors.Primary,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    text = if (copied) "Copied!" else "Copy",
                    color = if (copied) NeuroColors.Success else NeuroColors.Primary,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Medium
                )
            }
        }

        // Code content
        if (language == "diff") {
            DiffContent(trimmedCode)
        } else {
            val highlighted = remember(trimmedCode, language) {
                highlightSyntax(trimmedCode, language)
            }
            Text(
                text = highlighted,
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
                lineHeight = 18.sp,
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(12.dp)
            )
        }
    }
}

@Composable
private fun DiffContent(code: String) {
    Column(modifier = Modifier.padding(horizontal = 4.dp, vertical = 8.dp)) {
        code.lines().forEach { line ->
            val (bgColor, textColor) = when {
                line.startsWith("+++") || line.startsWith("---") -> Color.Transparent to NeuroColors.TextMuted
                line.startsWith("+") -> NeuroColors.DiffAddedBackground to NeuroColors.DiffAddedText
                line.startsWith("-") -> NeuroColors.DiffRemovedBackground to NeuroColors.DiffRemovedText
                line.startsWith("@@") -> Color.Transparent to NeuroColors.DiffHunkText
                else -> Color.Transparent to NeuroColors.SyntaxDefault
            }
            Text(
                text = line,
                color = textColor,
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
                lineHeight = 18.sp,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(bgColor)
                    .padding(horizontal = 8.dp, vertical = 1.dp)
            )
        }
    }
}

// ─── Blockquote ──────────────────────────────────────────────────────

@Composable
private fun RenderBlockquote(node: BlockQuote) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
    ) {
        Box(
            modifier = Modifier
                .width(3.dp)
                .heightIn(min = 20.dp)
                .background(NeuroColors.BlockquoteBorder, RoundedCornerShape(1.5.dp))
        )
        Spacer(Modifier.width(10.dp))
        Column(
            modifier = Modifier
                .weight(1f)
                .background(NeuroColors.BlockquoteBackground, RoundedCornerShape(4.dp))
                .padding(8.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            var child = node.firstChild
            while (child != null) {
                RenderBlock(child)
                child = child.next
            }
        }
    }
}

// ─── Lists ───────────────────────────────────────────────────────────

@Composable
private fun RenderBulletList(node: BulletList) {
    Column(
        modifier = Modifier.padding(start = 8.dp, top = 2.dp, bottom = 2.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        var item = node.firstChild
        while (item != null) {
            if (item is ListItem) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "  \u2022  ",
                        color = NeuroColors.Primary,
                        fontSize = 15.sp
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        var child = item.firstChild
                        while (child != null) {
                            RenderBlock(child)
                            child = child.next
                        }
                    }
                }
            }
            item = item.next
        }
    }
}

@Composable
private fun RenderOrderedList(node: OrderedList) {
    Column(
        modifier = Modifier.padding(start = 8.dp, top = 2.dp, bottom = 2.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        var index = node.startNumber
        var item = node.firstChild
        while (item != null) {
            if (item is ListItem) {
                Row(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = "  $index.  ",
                        color = NeuroColors.Primary,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Medium
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        var child = item.firstChild
                        while (child != null) {
                            RenderBlock(child)
                            child = child.next
                        }
                    }
                }
                index++
            }
            item = item.next
        }
    }
}

// ─── Table ───────────────────────────────────────────────────────────

@Composable
private fun RenderTable(node: TableBlock) {
    val rows = mutableListOf<List<String>>()
    var isHeader = true
    var headerRowCount = 0

    var section = node.firstChild
    while (section != null) {
        when (section) {
            is TableHead -> {
                var row = section.firstChild
                while (row != null) {
                    if (row is TableRow) {
                        rows.add(collectTableRow(row))
                        headerRowCount++
                    }
                    row = row.next
                }
            }
            is TableBody -> {
                var row = section.firstChild
                while (row != null) {
                    if (row is TableRow) {
                        rows.add(collectTableRow(row))
                    }
                    row = row.next
                }
            }
        }
        section = section.next
    }

    if (rows.isEmpty()) return

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clip(RoundedCornerShape(8.dp))
            .border(0.5.dp, NeuroColors.TableBorder, RoundedCornerShape(8.dp))
            .horizontalScroll(rememberScrollState())
    ) {
        rows.forEachIndexed { index, row ->
            val isHeaderRow = index < headerRowCount
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .then(
                        if (isHeaderRow) Modifier.background(NeuroColors.TableHeaderBackground)
                        else Modifier
                    )
                    .padding(horizontal = 10.dp, vertical = 8.dp)
            ) {
                row.forEach { cell ->
                    Text(
                        text = cell.trim(),
                        modifier = Modifier
                            .weight(1f)
                            .padding(horizontal = 4.dp),
                        color = if (isHeaderRow) NeuroColors.TextPrimary else NeuroColors.TextSecondary,
                        fontSize = 13.sp,
                        fontWeight = if (isHeaderRow) FontWeight.SemiBold else FontWeight.Normal,
                        lineHeight = 18.sp
                    )
                }
            }
            if (index < rows.lastIndex) {
                HorizontalDivider(thickness = 0.5.dp, color = NeuroColors.TableBorder)
            }
        }
    }
}

private fun collectTableRow(row: TableRow): List<String> {
    val cells = mutableListOf<String>()
    var cell = row.firstChild
    while (cell != null) {
        if (cell is TableCell) {
            cells.add(collectText(cell))
        }
        cell = cell.next
    }
    return cells
}

// ─── Horizontal rule ─────────────────────────────────────────────────

@Composable
private fun RenderHorizontalRule() {
    HorizontalDivider(
        thickness = 0.5.dp,
        color = NeuroColors.HorizontalRuleColor,
        modifier = Modifier.padding(vertical = 8.dp)
    )
}

// ─── Inline text building ────────────────────────────────────────────

private fun buildInlineAnnotatedString(node: Node): AnnotatedString {
    return buildAnnotatedString {
        appendInlineChildren(node)
    }
}

private fun AnnotatedString.Builder.appendInlineChildren(node: Node) {
    var child = node.firstChild
    while (child != null) {
        appendInlineNode(child)
        child = child.next
    }
}

private fun AnnotatedString.Builder.appendInlineNode(node: Node) {
    when (node) {
        is org.commonmark.node.Text -> append(node.literal)
        is Code -> {
            withStyle(SpanStyle(
                fontFamily = FontFamily.Monospace,
                fontSize = 13.sp,
                background = NeuroColors.InlineCodeBackground,
                color = NeuroColors.SyntaxDefault
            )) {
                append("\u2009${node.literal}\u2009") // thin space padding
            }
        }
        is Emphasis -> {
            withStyle(SpanStyle(fontStyle = FontStyle.Italic)) {
                appendInlineChildren(node)
            }
        }
        is StrongEmphasis -> {
            withStyle(SpanStyle(fontWeight = FontWeight.Bold, color = NeuroColors.TextPrimary)) {
                appendInlineChildren(node)
            }
        }
        is Link -> {
            pushStringAnnotation(tag = "URL", annotation = node.destination)
            withStyle(SpanStyle(
                color = NeuroColors.LinkColor,
                textDecoration = TextDecoration.Underline
            )) {
                appendInlineChildren(node)
            }
            pop()
        }
        is Strikethrough -> {
            withStyle(SpanStyle(textDecoration = TextDecoration.LineThrough)) {
                appendInlineChildren(node)
            }
        }
        is SoftLineBreak -> append(" ")
        is HardLineBreak -> append("\n")
        is Image -> {
            // Show alt text for images
            withStyle(SpanStyle(color = NeuroColors.TextMuted, fontStyle = FontStyle.Italic)) {
                append("[image: ")
                appendInlineChildren(node)
                append("]")
            }
        }
        is HtmlInline -> append(node.literal)
        else -> appendInlineChildren(node) // recurse for unknown inline containers
    }
}

// ─── Text collection utility ─────────────────────────────────────────

private fun collectText(node: Node): String {
    val sb = StringBuilder()
    fun walk(n: Node) {
        when (n) {
            is org.commonmark.node.Text -> sb.append(n.literal)
            is Code -> sb.append(n.literal)
            is SoftLineBreak -> sb.append(" ")
            is HardLineBreak -> sb.append("\n")
            else -> {
                var child = n.firstChild
                while (child != null) {
                    walk(child)
                    child = child.next
                }
            }
        }
    }
    walk(node)
    return sb.toString()
}

// ─── Syntax highlighting ─────────────────────────────────────────────

private fun highlightSyntax(code: String, language: String?): AnnotatedString {
    if (language == null) {
        return buildAnnotatedString {
            withStyle(SpanStyle(color = NeuroColors.SyntaxDefault)) { append(code) }
        }
    }

    val lang = language.lowercase()
    return buildAnnotatedString {
        when (lang) {
            "json" -> highlightJson(code)
            "kotlin", "kt" -> highlightKotlinLike(code)
            "java" -> highlightKotlinLike(code)
            "python", "py" -> highlightPython(code)
            "javascript", "js", "typescript", "ts" -> highlightJavaScript(code)
            "html", "xml" -> highlightHtml(code)
            "css" -> highlightCss(code)
            "bash", "sh", "shell", "zsh" -> highlightBash(code)
            "sql" -> highlightSql(code)
            else -> withStyle(SpanStyle(color = NeuroColors.SyntaxDefault)) { append(code) }
        }
    }
}

// --- JSON ---
private fun AnnotatedString.Builder.highlightJson(code: String) {
    val regex = Regex("""("(?:[^"\\]|\\.)*")\s*:|("(?:[^"\\]|\\.)*")|(true|false|null)|(-?\d+\.?\d*(?:[eE][+-]?\d+)?)|([{}\[\]:,])|(//.*|/\*[\s\S]*?\*/)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxType)     // key
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)   // string value
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)  // bool/null
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)   // number
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.TextMuted)      // punctuation
            match.groupValues[6].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)  // comment
            else -> null
        }
    }
}

// --- Kotlin/Java ---
private fun AnnotatedString.Builder.highlightKotlinLike(code: String) {
    val keywords = "abstract|actual|annotation|as|break|by|catch|class|companion|const|constructor|continue|crossinline|data|delegate|do|dynamic|else|enum|expect|external|false|final|finally|for|fun|get|if|import|in|infix|init|inline|inner|interface|internal|is|it|lateinit|lazy|noinline|null|object|open|operator|out|override|package|private|protected|public|reified|return|sealed|set|super|suspend|this|throw|true|try|typealias|typeof|val|var|vararg|when|where|while|void|int|long|float|double|boolean|byte|char|short|String|Int|Long|Float|Double|Boolean|List|Map|Set|Array"
    val regex = Regex("""(//.*|/\*[\s\S]*?\*/)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b($keywords)\b|\b([A-Z]\w*)\b|(@\w+)|(\b\d+\.?\d*[fLdD]?\b)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxType)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxFunction)
            match.groupValues[6].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// --- Python ---
private fun AnnotatedString.Builder.highlightPython(code: String) {
    val keywords = "and|as|assert|async|await|break|class|continue|def|del|elif|else|except|False|finally|for|from|global|if|import|in|is|lambda|None|nonlocal|not|or|pass|raise|return|True|try|while|with|yield|self|print"
    val regex = Regex("""(#.*)|(""{3}[\s\S]*?""{3}|'{3}[\s\S]*?'{3}|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b($keywords)\b|\b([A-Z]\w*)\b|(\b\d+\.?\d*\b)|(\bdef\s+)(\w+)|(\bclass\s+)(\w+)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxType)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// --- JavaScript/TypeScript ---
private fun AnnotatedString.Builder.highlightJavaScript(code: String) {
    val keywords = "async|await|break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|false|finally|for|from|function|if|import|in|instanceof|let|new|null|of|return|static|super|switch|this|throw|true|try|typeof|undefined|var|void|while|with|yield|interface|type|enum|implements|public|private|protected"
    val regex = Regex("""(//.*|/\*[\s\S]*?\*/)|(`(?:[^`\\]|\\.)*`|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|\b($keywords)\b|\b([A-Z]\w*)\b|(\b\d+\.?\d*\b)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxType)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// --- HTML/XML ---
private fun AnnotatedString.Builder.highlightHtml(code: String) {
    val regex = Regex("""(<!--[\s\S]*?-->)|(</?[a-zA-Z][\w-]*)|(>)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\w+)(?==)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxFunction)
            else -> null
        }
    }
}

// --- CSS ---
private fun AnnotatedString.Builder.highlightCss(code: String) {
    val regex = Regex("""(/\*[\s\S]*?\*/)|(#[\w-]+|\.[\w-]+)|([a-zA-Z-]+)(?=\s*:)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+\.?\d*(?:px|em|rem|%|vh|vw|deg|s|ms)?\b)|(#[0-9a-fA-F]{3,8})""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxFunction)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxType)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            match.groupValues[6].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// --- Bash/Shell ---
private fun AnnotatedString.Builder.highlightBash(code: String) {
    val keywords = "if|then|else|elif|fi|for|while|do|done|case|esac|function|return|exit|in|select|until|export|source|alias|unalias|local|readonly|declare|typeset|echo|printf|cd|ls|grep|awk|sed|cat|mkdir|rm|cp|mv|chmod|chown|sudo|apt|pip|npm|git|docker"
    val regex = Regex("""(#.*)|(\"(?:[^\"\\]|\\.)*\"|'[^']*')|\b($keywords)\b|(\$\{?\w+\}?)|(\b\d+\.?\d*\b)""")
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxFunction)
            match.groupValues[5].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// --- SQL ---
private fun AnnotatedString.Builder.highlightSql(code: String) {
    val keywords = "SELECT|FROM|WHERE|INSERT|INTO|UPDATE|SET|DELETE|CREATE|DROP|ALTER|TABLE|INDEX|VIEW|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|IS|NULL|AS|ORDER|BY|GROUP|HAVING|LIMIT|OFFSET|UNION|ALL|DISTINCT|EXISTS|BETWEEN|LIKE|CASE|WHEN|THEN|ELSE|END|BEGIN|COMMIT|ROLLBACK|PRIMARY|KEY|FOREIGN|REFERENCES|DEFAULT|VALUES|COUNT|SUM|AVG|MAX|MIN"
    val regex = Regex("""(--.*|/\*[\s\S]*?\*/)|('(?:[^'\\]|\\.)*')|\b($keywords)\b|\b(\d+\.?\d*)\b""", RegexOption.IGNORE_CASE)
    highlightWithRegex(code, regex) { match ->
        when {
            match.groupValues[1].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxComment)
            match.groupValues[2].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxString)
            match.groupValues[3].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxKeyword)
            match.groupValues[4].isNotEmpty() -> SpanStyle(color = NeuroColors.SyntaxNumber)
            else -> null
        }
    }
}

// ─── Shared regex highlighter ────────────────────────────────────────

private fun AnnotatedString.Builder.highlightWithRegex(
    code: String,
    regex: Regex,
    styleFor: (MatchResult) -> SpanStyle?
) {
    var lastIndex = 0
    for (match in regex.findAll(code)) {
        // Append text before this match as default
        if (match.range.first > lastIndex) {
            withStyle(SpanStyle(color = NeuroColors.SyntaxDefault)) {
                append(code.substring(lastIndex, match.range.first))
            }
        }
        val style = styleFor(match)
        if (style != null) {
            withStyle(style) { append(match.value) }
        } else {
            withStyle(SpanStyle(color = NeuroColors.SyntaxDefault)) { append(match.value) }
        }
        lastIndex = match.range.last + 1
    }
    // Remaining text
    if (lastIndex < code.length) {
        withStyle(SpanStyle(color = NeuroColors.SyntaxDefault)) {
            append(code.substring(lastIndex))
        }
    }
}
