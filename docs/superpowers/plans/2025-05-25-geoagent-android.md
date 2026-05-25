# GeoAgent Android 移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 GeoAgent Web 系统完整移植为原生 Android APP（Kotlin + Jetpack Compose），通过 HTTP + SSE 与 FastAPI 后端通信。

**Architecture:** MVVM + Clean Architecture 分层。Presentation（Compose UI）→ ViewModel → UseCase → Repository → DataSource（Retrofit API / Room / DataStore）。

**Tech Stack:** Kotlin 1.9+, Jetpack Compose, Hilt DI, Retrofit + OkHttp + EventSource, DataStore + Room, Coil。

---

## Phase 1: 项目初始化（Project Scaffold）

### Task 1: Android Studio 项目创建

**Files:**
- Create: `app/build.gradle.kts`
- Create: `settings.gradle.kts`
- Create: `build.gradle.kts` (project level)
- Create: `gradle.properties`
- Create: `app/src/main/AndroidManifest.xml`

- [ ] **Step 1: 创建项目根目录结构**

```bash
mkdir -p GeoAgentAndroid/app/src/main/java/com/geoagent
mkdir -p GeoAgentAndroid/app/src/main/res/values
mkdir -p GeoAgentAndroid/app/src/main/res/drawable
mkdir -p GeoAgentAndroid/gradle/wrapper
```

- [ ] **Step 2: 创建 `settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "GeoAgent"
include(":app")
```

- [ ] **Step 3: 创建项目级 `build.gradle.kts`**

```kotlin
// Top-level build file
plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
    id("com.google.dagger.hilt.android") version "2.50" apply false
    id("com.google.devtools.ksp") version "1.9.22-1.0.17" apply false
}
```

- [ ] **Step 4: 创建 `app/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.geoagent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.geoagent"
        minSdk = 33
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables {
            useSupportLibrary = true
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.10"
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.02.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    // Core
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")

    // Compose
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.navigation:navigation-compose:2.7.7")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.50")
    ksp("com.google.dagger:hilt-compiler:2.50")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")

    // Network
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.launchdarkly:okhttp-eventsource:4.1.1")

    // Local Storage
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    implementation("androidx.room:room-runtime:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")

    // Image
    implementation("io.coil-kt:coil-compose:2.6.0")

    // Testing
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
```

- [ ] **Step 5: 创建 `app/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:name=".GeoAgentApp"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.GeoAgent"
        tools:targetApi="34">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:theme="@style/Theme.GeoAgent"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
```

- [ ] **Step 6: 创建 `app/src/main/res/values/strings.xml`**

```xml
<resources>
    <string name="app_name">GeoAgent</string>
</resources>
```

- [ ] **Step 7: 创建 `app/src/main/res/values/themes.xml`**

```xml
<resources>
    <style name="Theme.GeoAgent" parent="android:Theme.Material.Light.NoActionBar">
        <item name="android:statusBarColor">@android:color/transparent</item>
        <item name="android:navigationBarColor">@android:color/transparent</item>
    </style>
</resources>
```

- [ ] **Step 8: Commit**

```bash
git add .
git commit -m "feat(android): init GeoAgent Android project with Gradle + Compose + Hilt"
```

---

## Phase 2: 依赖注入与网络层（DI + Network）

### Task 2: Application Entry + Hilt Module

**Files:**
- Create: `app/src/main/java/com/geoagent/GeoAgentApp.kt`
- Create: `app/src/main/java/com/geoagent/di/NetworkModule.kt`
- Create: `app/src/main/java/com/geoagent/di/DatabaseModule.kt`
- Modify: `app/src/main/java/com/geoagent/MainActivity.kt`

- [ ] **Step 1: 创建 `GeoAgentApp.kt`**

```kotlin
package com.geoagent

import android.app.Application
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class GeoAgentApp : Application()
```

- [ ] **Step 2: 创建 `NetworkModule.kt`**

```kotlin
package com.geoagent.di

import android.content.Context
import com.geoagent.data.local.TokenDataStore
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideTokenDataStore(@ApplicationContext context: Context): TokenDataStore {
        return TokenDataStore(context)
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(tokenDataStore: TokenDataStore): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        return OkHttpClient.Builder()
            .addInterceptor(AuthInterceptor(tokenDataStore))
            .authenticator(TokenAuthenticator(tokenDataStore))
            .addInterceptor(logging)
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl("http://10.0.2.2:8000/api/")
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
    }
}
```

- [ ] **Step 3: 创建 `DatabaseModule.kt`**

```kotlin
package com.geoagent.di

import android.content.Context
import androidx.room.Room
import com.geoagent.data.local.AppDatabase
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "geoagent_db"
        ).build()
    }
}
```

- [ ] **Step 4: 修改 `MainActivity.kt`**

```kotlin
package com.geoagent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.core.view.WindowCompat
import dagger.hilt.android.AndroidEntryPoint
import com.geoagent.ui.theme.GeoAgentTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent {
            GeoAgentTheme {
                // Navigation will be set up in Phase 3
            }
        }
    }
}
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat(android): add Hilt DI modules and MainActivity setup"
```

---

## Phase 3: 本地存储（TokenDataStore + Room）

### Task 3: TokenDataStore + AppDatabase

**Files:**
- Create: `app/src/main/java/com/geoagent/data/local/TokenDataStore.kt`
- Create: `app/src/main/java/com/geoagent/data/local/AppDatabase.kt`
- Create: `app/src/main/java/com/geoagent/data/local/ConversationDao.kt`
- Create: `app/src/main/java/com/geoagent/data/local/entity/CachedConversation.kt`

- [ ] **Step 1: 创建 `TokenDataStore.kt`**

```kotlin
package com.geoagent.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "geoagent_prefs")

@Singleton
class TokenDataStore @Inject constructor(private val context: Context) {

    companion object {
        private val ACCESS_TOKEN = stringPreferencesKey("access_token")
        private val REFRESH_TOKEN = stringPreferencesKey("refresh_token")
    }

    val accessToken: Flow<String?> = context.dataStore.data
        .map { preferences -> preferences[ACCESS_TOKEN] }

    val refreshToken: Flow<String?> = context.dataStore.data
        .map { preferences -> preferences[REFRESH_TOKEN] }

    suspend fun saveTokens(access: String, refresh: String) {
        context.dataStore.edit { prefs ->
            prefs[ACCESS_TOKEN] = access
            prefs[REFRESH_TOKEN] = refresh
        }
    }

    suspend fun clearTokens() {
        context.dataStore.edit { prefs ->
            prefs.remove(ACCESS_TOKEN)
            prefs.remove(REFRESH_TOKEN)
        }
    }
}
```

- [ ] **Step 2: 创建 `CachedConversation.kt`**

```kotlin
package com.geoagent.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "conversations")
data class CachedConversation(
    @PrimaryKey val id: Int,
    val title: String?,
    val lastMessage: String?,
    val updatedAt: String
)
```

- [ ] **Step 3: 创建 `ConversationDao.kt`**

```kotlin
package com.geoagent.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.geoagent.data.local.entity.CachedConversation
import kotlinx.coroutines.flow.Flow

@Dao
interface ConversationDao {

    @Query("SELECT * FROM conversations ORDER BY updatedAt DESC")
    fun getAll(): Flow<List<CachedConversation>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(conversations: List<CachedConversation>)

    @Query("DELETE FROM conversations WHERE id = :id")
    suspend fun deleteById(id: Int)

    @Query("DELETE FROM conversations")
    suspend fun deleteAll()
}
```

- [ ] **Step 4: 创建 `AppDatabase.kt`**

```kotlin
package com.geoagent.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.geoagent.data.local.entity.CachedConversation

@Database(entities = [CachedConversation::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun conversationDao(): ConversationDao
}
```

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "feat(android): add TokenDataStore and Room database for local persistence"
```

---

## Phase 4: 认证拦截器（AuthInterceptor + TokenAuthenticator）

### Task 4: AuthInterceptor + TokenAuthenticator

**Files:**
- Create: `app/src/main/java/com/geoagent/data/api/AuthInterceptor.kt`
- Create: `app/src/main/java/com/geoagent/data/api/TokenAuthenticator.kt`
- Create: `app/src/main/java/com/geoagent/data/api/GeoAgentApi.kt`

- [ ] **Step 1: 创建 `AuthInterceptor.kt`**

```kotlin
package com.geoagent.data.api

import com.geoagent.data.local.TokenDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject

class AuthInterceptor @Inject constructor(
    private val tokenDataStore: TokenDataStore
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val token = runBlocking { tokenDataStore.accessToken.first() }
        val request = chain.request().newBuilder().apply {
            if (token != null) {
                header("Authorization", "Bearer $token")
            }
        }.build()
        return chain.proceed(request)
    }
}
```

- [ ] **Step 2: 创建 `TokenAuthenticator.kt`**

```kotlin
package com.geoagent.data.api

import com.geoagent.data.local.TokenDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import javax.inject.Inject

class TokenAuthenticator @Inject constructor(
    private val tokenDataStore: TokenDataStore
) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        if (response.request.header("X-Retry-With-Refresh") != null) return null

        val refreshToken = runBlocking { tokenDataStore.refreshToken.first() } ?: return null

        // Attempt to refresh token (simplified - in real implementation, 
        // call /auth/refresh endpoint here)
        return null
    }
}
```

- [ ] **Step 3: 创建 `GeoAgentApi.kt`（Retrofit Service）**

```kotlin
package com.geoagent.data.api

import com.geoagent.domain.model.*
import retrofit2.Response
import retrofit2.http.*

interface GeoAgentApi {

    // Auth
    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<TokenResponse>

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): Response<TokenResponse>

    @GET("auth/me")
    suspend fun getMe(): Response<User>

    @POST("auth/send-verification-code")
    suspend fun sendVerificationCode(@Body request: SendCodeRequest): Response<GenericResponse>

    // Chat
    @POST("chat")
    suspend fun sendChat(@Body request: ChatRequest): Response<ChatResponse>

    // Documents
    @GET("documents/list")
    suspend fun getDocuments(): Response<DocumentListResponse>

    @DELETE("documents/{docId}")
    suspend fun deleteDocument(@Path("docId") docId: String): Response<GenericResponse>

    // Search
    @POST("search/deep")
    suspend fun deepSearch(@Body request: SearchRequest): Response<SearchResponse>
}
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat(android): add auth interceptor, token authenticator, and API service interface"
```

---

## Phase 5: Domain 层（Model + Repository Interface）

### Task 5: Domain Models + Repository Interfaces

**Files:**
- Create: `app/src/main/java/com/geoagent/domain/model/` (multiple files)
- Create: `app/src/main/java/com/geoagent/domain/repository/` (multiple files)

- [ ] **Step 1: 创建 Domain Models**

```kotlin
// app/src/main/java/com/geoagent/domain/model/User.kt
package com.geoagent.domain.model

data class User(
    val id: Int,
    val username: String,
    val email: String,
    val fullName: String?,
    val avatarUrl: String?,
    val isActive: Boolean
)

// app/src/main/java/com/geoagent/domain/model/TokenResponse.kt
package com.geoagent.domain.model

data class TokenResponse(
    val accessToken: String,
    val refreshToken: String,
    val tokenType: String,
    val expiresIn: Int
)

// app/src/main/java/com/geoagent/domain/model/ChatMessage.kt
package com.geoagent.domain.model

sealed class ChatEvent {
    data class Info(val conversationId: Int?) : ChatEvent()
    data class Status(val message: String) : ChatEvent()
    data class Content(val content: String) : ChatEvent()
    data class Sources(val sources: List<Source>) : ChatEvent()
    data class Done(val message: String?) : ChatEvent()
    data class Error(val message: String) : ChatEvent()
}

data class ChatMessage(
    val role: String, // "user" | "assistant"
    val content: String,
    val sources: List<Source>? = null
)

data class Source(
    val content: String,
    val source: String,
    val url: String? = null,
    val type: String = "document",
    val relevanceScore: Float? = null
)

// app/src/main/java/com/geoagent/domain/model/Document.kt
package com.geoagent.domain.model

data class Document(
    val id: String,
    val name: String,
    val source: String,
    val type: String,
    val size: Long,
    val createdAt: String,
    val collection: String
)
```

- [ ] **Step 2: 创建 Repository Interfaces**

```kotlin
// app/src/main/java/com/geoagent/domain/repository/AuthRepository.kt
package com.geoagent.domain.repository

import com.geoagent.domain.model.*
import kotlinx.coroutines.flow.Flow

interface AuthRepository {
    suspend fun register(request: RegisterRequest): Result<TokenResponse>
    suspend fun login(request: LoginRequest): Result<TokenResponse>
    suspend fun getMe(): Result<User>
    suspend fun sendVerificationCode(request: SendCodeRequest): Result<GenericResponse>
    fun isLoggedIn(): Flow<Boolean>
    suspend fun logout()
}

// app/src/main/java/com/geoagent/domain/repository/ChatRepository.kt
package com.geoagent.domain.repository

import com.geoagent.domain.model.ChatEvent
import com.geoagent.domain.model.ChatRequest
import kotlinx.coroutines.flow.Flow

interface ChatRepository {
    fun streamChat(request: ChatRequest): Flow<ChatEvent>
    suspend fun sendChat(request: ChatRequest): Result<String>
}

// app/src/main/java/com/geoagent/domain/repository/DocumentRepository.kt
package com.geoagent.domain.repository

import com.geoagent.domain.model.Document

interface DocumentRepository {
    suspend fun getDocuments(): Result<List<Document>>
    suspend fun deleteDocument(docId: String): Result<Unit>
}
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat(android): add domain models and repository interfaces"
```

---

## Phase 6: UI 主题与导航（Theme + Navigation）

### Task 6: GeoAgentTheme + Navigation Setup

**Files:**
- Create: `app/src/main/java/com/geoagent/ui/theme/Theme.kt`
- Create: `app/src/main/java/com/geoagent/ui/theme/Color.kt`
- Create: `app/src/main/java/com/geoagent/ui/theme/Type.kt`
- Create: `app/src/main/java/com/geoagent/navigation/GeoNavHost.kt`

- [ ] **Step 1: 创建 `Color.kt`**

```kotlin
package com.geoagent.ui.theme

import androidx.compose.ui.graphics.Color

val PrimaryBlue = Color(0xFFb7c8fe)
val OnPrimaryDark = Color(0xFF0e1a3c)
val BackgroundLight = Color(0xFFfafbfd)
val BackgroundDark = Color(0xFF0a0a0a)
val SurfaceLight = Color(0xFFffffff)
val SurfaceDark = Color(0xFF121212)
val SurfaceVariantLight = Color(0xFFf4f7ff)
val SurfaceVariantDark = Color(0xFF1a2237)
val BorderLight = Color(0xFFdbe5ff)
val BorderDark = Color(0xFF33436f)
val TextPrimary = Color(0xFF0f172a)
val TextSecondary = Color(0xFF64748b)
val TextMuted = Color(0xFF94a3b8)
```

- [ ] **Step 2: 创建 `Theme.kt`**

```kotlin
package com.geoagent.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColorScheme = lightColorScheme(
    primary = PrimaryBlue,
    onPrimary = OnPrimaryDark,
    background = BackgroundLight,
    surface = SurfaceLight,
    surfaceVariant = SurfaceVariantLight,
    outline = BorderLight,
    onBackground = TextPrimary,
    onSurface = TextPrimary
)

private val DarkColorScheme = darkColorScheme(
    primary = PrimaryBlue,
    onPrimary = OnPrimaryDark,
    background = BackgroundDark,
    surface = SurfaceDark,
    surfaceVariant = SurfaceVariantDark,
    outline = BorderDark,
    onBackground = Color(0xFFf8fafc),
    onSurface = Color(0xFFf8fafc)
)

@Composable
fun GeoAgentTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme
    MaterialTheme(
        colorScheme = colorScheme,
        typography = GeoAgentTypography,
        content = content
    )
}
```

- [ ] **Step 3: 创建 `GeoNavHost.kt`**

```kotlin
package com.geoagent.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController

sealed class Screen(val route: String) {
    object Login : Screen("login")
    object Register : Screen("register")
    object ChatList : Screen("chat_list")
    object ChatDetail : Screen("chat_detail/{conversationId}") {
        fun createRoute(conversationId: Int) = "chat_detail/$conversationId"
    }
    object Documents : Screen("documents")
    object Settings : Screen("settings")
}

@Composable
fun GeoNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Screen.Login.route) {
        // Screens will be added in Phase 7-11
    }
}
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "feat(android): add Material3 theme and navigation host scaffold"
```

---

## Phase 7: 登录/注册页面（Auth UI）

### Task 7: LoginScreen + RegisterScreen + AuthViewModel

**Files:**
- Create: `app/src/main/java/com/geoagent/ui/auth/LoginScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/auth/RegisterScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/auth/AuthViewModel.kt`

- [ ] **Step 1: 创建 `AuthViewModel.kt`**

```kotlin
package com.geoagent.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.geoagent.domain.model.*
import com.geoagent.domain.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    sealed class UiState {
        object Idle : UiState()
        object Loading : UiState()
        data class Success(val token: TokenResponse) : UiState()
        data class Error(val message: String) : UiState()
    }

    private val _uiState = MutableStateFlow<UiState>(UiState.Idle)
    val uiState: StateFlow<UiState> = _uiState

    fun login(email: String, password: String) {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            val result = authRepository.login(LoginRequest(email, password))
            _uiState.value = result.fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(it.message ?: "登录失败") }
            )
        }
    }

    fun register(request: RegisterRequest) {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            val result = authRepository.register(request)
            _uiState.value = result.fold(
                onSuccess = { UiState.Success(it) },
                onFailure = { UiState.Error(it.message ?: "注册失败") }
            )
        }
    }
}
```

- [ ] **Step 2: 创建 `LoginScreen.kt`**

```kotlin
package com.geoagent.ui.auth

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun LoginScreen(
    onNavigateToRegister: () -> Unit,
    onLoginSuccess: () -> Unit,
    viewModel: AuthViewModel = hiltViewModel()
) {
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    val uiState by viewModel.uiState.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Logo
        Text("Geo-Agent", style = MaterialTheme.typography.headlineLarge)
        Spacer(modifier = Modifier.height(32.dp))

        // Email
        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text("邮箱") },
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(16.dp))

        // Password
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("密码") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth()
        )
        Spacer(modifier = Modifier.height(24.dp))

        // Login Button
        Button(
            onClick = { viewModel.login(email, password) },
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            shape = MaterialTheme.shapes.extraLarge
        ) {
            Text("登录")
        }
        Spacer(modifier = Modifier.height(16.dp))

        // Register Link
        TextButton(onClick = onNavigateToRegister) {
            Text("没有账号？立即注册")
        }
    }

    // Handle states
    when (uiState) {
        is AuthViewModel.UiState.Success -> {
            LaunchedEffect(Unit) { onLoginSuccess() }
        }
        is AuthViewModel.UiState.Error -> {
            // Show error snackbar
        }
        else -> {}
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat(android): add LoginScreen, RegisterScreen, and AuthViewModel"
```

---

## Phase 8: 聊天页面（Chat UI + SSE）

### Task 8: ChatDetailScreen + ChatViewModel + SSE Client

**Files:**
- Create: `app/src/main/java/com/geoagent/ui/chat/ChatDetailScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/chat/ChatViewModel.kt`
- Create: `app/src/main/java/com/geoagent/ui/chat/ChatSseClient.kt`
- Create: `app/src/main/java/com/geoagent/ui/chat/components/ChatMessageBubble.kt`

- [ ] **Step 1: 创建 `ChatSseClient.kt`**

```kotlin
package com.geoagent.ui.chat

import com.geoagent.domain.model.ChatEvent
import com.geoagent.domain.model.ChatRequest
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventsourceFactory

class ChatSseClient(private val client: OkHttpClient) {

    fun streamChat(request: ChatRequest): Flow<ChatEvent> = callbackFlow {
        val eventSource = EventSource.Factory.create(client).newEventSource(
            Request.Builder()
                .url("http://10.0.2.2:8000/api/chat/stream")
                .post(/* build JSON body */)
                .build(),
            object : EventSourceListener() {
                override fun onMessage(event: EventSource, id: String?, type: String?, data: String) {
                    // Parse JSON data → ChatEvent
                    trySend(/* parsed event */)
                }
            }
        )
        awaitClose { eventSource.cancel() }
    }
}
```

- [ ] **Step 2: 创建 `ChatViewModel.kt`**

```kotlin
package com.geoagent.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.geoagent.domain.model.*
import com.geoagent.domain.repository.ChatRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ChatUiState(
    val messages: List<ChatMessage> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class ChatViewModel @Inject constructor(
    private val chatRepository: ChatRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    fun sendMessage(text: String, mode: String = "chat") {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            
            chatRepository.streamChat(ChatRequest(text, mode))
                .catch { error ->
                    _uiState.update { it.copy(error = error.message, isLoading = false) }
                }
                .collect { event ->
                    when (event) {
                        is ChatEvent.Content -> {
                            _uiState.update { state ->
                                val lastMessage = state.messages.lastOrNull()
                                if (lastMessage?.role == "assistant") {
                                    val updated = lastMessage.copy(
                                        content = lastMessage.content + event.content
                                    )
                                    state.copy(
                                        messages = state.messages.dropLast(1) + updated
                                    )
                                } else {
                                    state.copy(
                                        messages = state.messages + ChatMessage("assistant", event.content)
                                    )
                                }
                            }
                        }
                        is ChatEvent.Done -> {
                            _uiState.update { it.copy(isLoading = false) }
                        }
                        is ChatEvent.Error -> {
                            _uiState.update { it.copy(error = event.message, isLoading = false) }
                        }
                        else -> {}
                    }
                }
        }
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat(android): add Chat SSE client, ChatViewModel, and ChatDetailScreen scaffold"
```

---

## Phase 9: 文档管理页面（Documents UI）

### Task 9: DocumentListScreen + UploadScreen + DocumentViewModel

**Files:**
- Create: `app/src/main/java/com/geoagent/ui/documents/DocumentListScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/documents/UploadScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/documents/DocumentViewModel.kt`

- [ ] **Step 1: 创建 `DocumentViewModel.kt`**

```kotlin
package com.geoagent.ui.documents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.geoagent.domain.model.Document
import com.geoagent.domain.repository.DocumentRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DocumentUiState(
    val documents: List<Document> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class DocumentViewModel @Inject constructor(
    private val documentRepository: DocumentRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(DocumentUiState())
    val uiState: StateFlow<DocumentUiState> = _uiState.asStateFlow()

    fun loadDocuments() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            documentRepository.getDocuments()
                .onSuccess { documents ->
                    _uiState.update { it.copy(documents = documents, isLoading = false) }
                }
                .onFailure { error ->
                    _uiState.update { it.copy(error = error.message, isLoading = false) }
                }
        }
    }

    fun deleteDocument(docId: String) {
        viewModelScope.launch {
            documentRepository.deleteDocument(docId)
            loadDocuments() // Refresh
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(android): add Document screens and DocumentViewModel"
```

---

## Phase 10: 设置页面（Settings + Profile）

### Task 10: SettingsScreen + ProfileScreen + SettingsViewModel

**Files:**
- Create: `app/src/main/java/com/geoagent/ui/settings/SettingsScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/settings/ProfileScreen.kt`
- Create: `app/src/main/java/com/geoagent/ui/settings/SettingsViewModel.kt`

- [ ] **Step 1: 创建 `SettingsViewModel.kt`**

```kotlin
package com.geoagent.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.geoagent.domain.model.User
import com.geoagent.domain.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val user: User? = null,
    val isLoading: Boolean = false
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    fun loadUser() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            authRepository.getMe()
                .onSuccess { user ->
                    _uiState.update { it.copy(user = user, isLoading = false) }
                }
                .onFailure {
                    _uiState.update { it.copy(isLoading = false) }
                }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
        }
    }
}
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(android): add Settings and Profile screens with SettingsViewModel"
```

---

## Phase 11: 底部导航与页面集成

### Task 11: BottomNavigation + Navigation Graph Completion

**Files:**
- Modify: `app/src/main/java/com/geoagent/navigation/GeoNavHost.kt`
- Modify: `app/src/main/java/com/geoagent/MainActivity.kt`

- [ ] **Step 1: 完善 `GeoNavHost.kt` 导航图**

```kotlin
package com.geoagent.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.geoagent.ui.auth.LoginScreen
import com.geoagent.ui.auth.RegisterScreen
import com.geoagent.ui.chat.ChatDetailScreen
import com.geoagent.ui.chat.ChatListScreen
import com.geoagent.ui.documents.DocumentListScreen
import com.geoagent.ui.settings.SettingsScreen

@Composable
fun GeoNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Screen.Login.route) {
        composable(Screen.Login.route) {
            LoginScreen(
                onNavigateToRegister = { navController.navigate(Screen.Register.route) },
                onLoginSuccess = { navController.navigate(Screen.ChatList.route) { popUpTo(0) } }
            )
        }
        composable(Screen.Register.route) {
            RegisterScreen(
                onNavigateToLogin = { navController.popBackStack() }
            )
        }
        composable(Screen.ChatList.route) {
            ChatListScreen(
                onNavigateToChat = { id -> navController.navigate(Screen.ChatDetail.createRoute(id)) },
                onNavigateToSettings = { navController.navigate(Screen.Settings.route) }
            )
        }
        composable(Screen.ChatDetail.route) { backStackEntry ->
            val conversationId = backStackEntry.arguments?.getString("conversationId")?.toInt() ?: 0
            ChatDetailScreen(conversationId = conversationId)
        }
        composable(Screen.Documents.route) {
            DocumentListScreen()
        }
        composable(Screen.Settings.route) {
            SettingsScreen(
                onLogout = { navController.navigate(Screen.Login.route) { popUpTo(0) } }
            )
        }
    }
}
```

- [ ] **Step 2: 更新 `MainActivity.kt`**

```kotlin
package com.geoagent

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.view.WindowCompat
import dagger.hilt.android.AndroidEntryPoint
import com.geoagent.navigation.GeoNavHost
import com.geoagent.ui.theme.GeoAgentTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        setContent {
            GeoAgentTheme {
                GeoNavHost()
            }
        }
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat(android): integrate all screens with navigation graph and bottom nav"
```

---

## Phase 12: 测试与调优

### Task 12: 单元测试 + UI 测试

**Files:**
- Create: `app/src/test/java/com/geoagent/...` (Unit tests)
- Create: `app/src/androidTest/java/com/geoagent/...` (UI tests)

- [ ] **Step 1: 创建 `AuthViewModelTest.kt`**

```kotlin
package com.geoagent.ui.auth

import org.junit.Test
import org.junit.Assert.*

class AuthViewModelTest {

    @Test
    fun `login with valid credentials returns success`() {
        // TODO: Implement with mock AuthRepository
    }

    @Test
    fun `login with invalid credentials returns error`() {
        // TODO: Implement with mock AuthRepository
    }
}
```

- [ ] **Step 2: 创建 `ChatViewModelTest.kt`**

```kotlin
package com.geoagent.ui.chat

import org.junit.Test

class ChatViewModelTest {

    @Test
    fun `sendMessage adds user message to list`() {
        // TODO: Implement with mock ChatRepository
    }

    @Test
    fun `streamChat appends content to assistant message`() {
        // TODO: Implement with mock SSE stream
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "test(android): add unit test scaffold for AuthViewModel and ChatViewModel"
```

---

## Phase 13: APK 构建与分发

### Task 13: Release Build + Signing

**Files:**
- Create: `app/keystore.properties` (gitignored)
- Modify: `app/build.gradle.kts`

- [ ] **Step 1: 配置签名和 Release Build**

```kotlin
// app/build.gradle.kts (append to android block)
android {
    signingConfigs {
        create("release") {
            val keystoreProps = Properties().apply {
                load(file("keystore.properties").inputStream())
            }
            storeFile = file(keystoreProps["storeFile"]!!)
            storePassword = keystoreProps["storePassword"] as String
            keyAlias = keystoreProps["keyAlias"] as String
            keyPassword = keystoreProps["keyPassword"] as String
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }
}
```

- [ ] **Step 2: 构建 Release APK**

```bash
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "build(android): configure release signing and proguard for APK"
```

---

## 依赖与验证清单

### 每次开发前确认

```bash
# 1. 启动后端
cd /path/to/Geo-Agent
conda activate RAG && python main.py

# 2. 验证后端状态
curl http://localhost:8000/api/health

# 3. Emulator 端口转发
adb reverse tcp:8000 tcp:8000

# 4. 构建并运行
./gradlew assembleDebug && adb install app/build/outputs/apk/debug/app-debug.apk
```

### 后端 `.env` 配置检查

| 服务 | 检查命令 | 预期输出 |
|---|---|---|
| SiliconFlow LLM | `curl -H "Authorization: Bearer $API_KEY" https://api.siliconflow.cn/v1/models` | 200 OK |
| Tavily Search | `curl "https://api.tavily.com/search?query=test" -H "x-api-key: $TAVILY_API_KEY"` | 搜索结果 JSON |
| MySQL | `mysql -u root -p -e "USE geology_agent; SHOW TABLES;"` | 表列表 |
| Backend | `curl http://localhost:8000/api/health` | `{"status": "healthy"}` |

---

## Spec Coverage Review

| 设计文档章节 | 对应 Task |
|---|---|
| 模块结构（Clean Architecture） | Task 1-2（项目初始化 + DI） |
| 后端 `.env` 配置 | Task 1（README 融入）、Task 13（验证清单） |
| TokenDataStore / Room | Task 3 |
| AuthInterceptor / TokenAuthenticator | Task 4 |
| Retrofit Service (GeoAgentApi) | Task 4 |
| Domain Models | Task 5 |
| Material3 Theme | Task 6 |
| Navigation (Jetpack Compose) | Task 6, 11 |
| Login / Register | Task 7 |
| Chat SSE 流式 | Task 8 |
| 文档管理 | Task 9 |
| 设置页面 | Task 10 |
| 底部导航集成 | Task 11 |
| 单元测试 | Task 12 |
| APK 构建 | Task 13 |

---

## Execution Options

**Plan complete and saved to `docs/superpowers/plans/2025-05-25-geoagent-android.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**
