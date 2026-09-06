package com.example.agrisense_seashark_app

import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.database.Cursor
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import androidx.core.content.FileProvider
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.agrisense.app/installer"
    private var downloadId: Long = -1L
    private var downloadReceiver: BroadcastReceiver? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "installApk" -> {
                    val filePath = call.argument<String>("filePath")
                    if (filePath != null) {
                        installApkFile(filePath, result)
                    } else {
                        result.error("INVALID_PATH", "File path is null", null)
                    }
                }
                "downloadInBackground" -> {
                    val url = call.argument<String>("url")
                    val fileName = call.argument<String>("fileName")
                    val title = call.argument<String>("title")
                    if (url != null && fileName != null) {
                        startSystemBackgroundDownload(url, fileName, title ?: "AgriSense Update", result)
                    } else {
                        result.error("INVALID_ARGS", "Missing url or fileName", null)
                    }
                }
                "cancelDownload" -> {
                    cancelCurrentDownload(result)
                }
                "getDownloadProgress" -> {
                    getDownloadProgressStatus(result)
                }
                else -> result.notImplemented()
            }
        }
    }

    private fun startSystemBackgroundDownload(url: String, fileName: String, title: String, result: MethodChannel.Result) {
        try {
            val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            
            // If previous download exists, remove it first
            if (downloadId != -1L) {
                try { downloadManager.remove(downloadId) } catch (e: Exception) {}
            }

            val uri = Uri.parse(url)
            val request = DownloadManager.Request(uri).apply {
                setTitle(title)
                setDescription("Downloading AgriSense Software Update Package...")
                setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName)
                setAllowedOverMetered(true)
                setAllowedOverRoaming(true)
            }
            downloadId = downloadManager.enqueue(request)

            if (downloadReceiver != null) {
                try { unregisterReceiver(downloadReceiver) } catch (e: Exception) {}
            }

            val filter = IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE)
            downloadReceiver = object : BroadcastReceiver() {
                override fun onReceive(context: Context?, intent: Intent?) {
                    val id = intent?.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
                    if (id == downloadId) {
                        val file = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), fileName)
                        if (file.exists()) {
                            installApkFile(file.absolutePath, null)
                        }
                    }
                }
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(downloadReceiver, filter, Context.RECEIVER_EXPORTED)
            } else {
                registerReceiver(downloadReceiver, filter)
            }

            result.success("Background download enqueued")
        } catch (e: Exception) {
            result.error("DOWNLOAD_ERROR", e.message, null)
        }
    }

    private fun cancelCurrentDownload(result: MethodChannel.Result) {
        try {
            if (downloadId != -1L) {
                val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
                downloadManager.remove(downloadId)
                downloadId = -1L
            }
            if (downloadReceiver != null) {
                try { unregisterReceiver(downloadReceiver) } catch (e: Exception) {}
                downloadReceiver = null
            }
            result.success("Download canceled")
        } catch (e: Exception) {
            result.error("CANCEL_ERROR", e.message, null)
        }
    }

    private fun getDownloadProgressStatus(result: MethodChannel.Result) {
        if (downloadId == -1L) {
            result.success(mapOf("status" to "idle", "bytes_so_far" to 0L, "total_bytes" to 0L))
            return
        }

        try {
            val downloadManager = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
            val query = DownloadManager.Query().setFilterById(downloadId)
            val cursor: Cursor = downloadManager.query(query)

            if (cursor.moveToFirst()) {
                val bytesDownloadedIndex = cursor.getColumnIndex(DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR)
                val bytesTotalIndex = cursor.getColumnIndex(DownloadManager.COLUMN_TOTAL_SIZE_BYTES)
                val statusIndex = cursor.getColumnIndex(DownloadManager.COLUMN_STATUS)

                val bytesDownloaded = if (bytesDownloadedIndex != -1) cursor.getLong(bytesDownloadedIndex) else 0L
                val bytesTotal = if (bytesTotalIndex != -1) cursor.getLong(bytesTotalIndex) else 0L
                val statusInt = if (statusIndex != -1) cursor.getInt(statusIndex) else -1

                val statusStr = when (statusInt) {
                    DownloadManager.STATUS_RUNNING -> "running"
                    DownloadManager.STATUS_SUCCESSFUL -> "successful"
                    DownloadManager.STATUS_FAILED -> "failed"
                    DownloadManager.STATUS_PENDING -> "pending"
                    DownloadManager.STATUS_PAUSED -> "paused"
                    else -> "unknown"
                }

                result.success(mapOf(
                    "status" to statusStr,
                    "bytes_so_far" to bytesDownloaded,
                    "total_bytes" to bytesTotal
                ))
            } else {
                result.success(mapOf("status" to "idle", "bytes_so_far" to 0L, "total_bytes" to 0L))
            }
            cursor.close()
        } catch (e: Exception) {
            result.error("QUERY_ERROR", e.message, null)
        }
    }

    private fun installApkFile(filePath: String, result: MethodChannel.Result?) {
        try {
            val file = File(filePath)
            if (!file.exists()) {
                result?.error("FILE_NOT_FOUND", "File does not exist: $filePath", null)
                return
            }

            // Check O+ Unknown App Sources Permission
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (!context.packageManager.canRequestPackageInstalls()) {
                    val manageIntent = Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                        data = Uri.parse("package:${context.packageName}")
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    }
                    context.startActivity(manageIntent)
                }
            }

            val intent = Intent(Intent.ACTION_VIEW)
            val apkUri: Uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                FileProvider.getUriForFile(
                    context,
                    "com.example.agrisense_seashark_app.fileprovider",
                    file
                )
            } else {
                Uri.fromFile(file)
            }
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            result?.success("Installer launched")
        } catch (e: Exception) {
            result?.error("INSTALL_ERROR", e.message, null)
        }
    }
}
