# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.kts.

# Keep Ktor
-keep class io.ktor.** { *; }
-keepclassmembers class io.ktor.** { *; }
-dontwarn io.ktor.**

# Keep Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlinx.serialization.json.** {
    *** Companion;
}
-keepclasseswithmembers class kotlinx.serialization.json.** {
    kotlinx.serialization.KSerializer serializer(...);
}
-keep,includedescriptorclasses class com.neurocomputer.neuromobile.**$$serializer { *; }
-keepclassmembers class com.neurocomputer.neuromobile.** {
    *** Companion;
}
-keepclasseswithmembers class com.neurocomputer.neuromobile.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Keep LiveKit
-keep class io.livekit.** { *; }
-keepclassmembers class io.livekit.** { *; }
-dontwarn io.livekit.**

# Keep ML Kit
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**
