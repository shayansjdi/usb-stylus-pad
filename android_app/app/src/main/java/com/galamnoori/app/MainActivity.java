package com.galamnoori.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;

public class MainActivity extends Activity {

    private WebView webView;
    private SharedPreferences prefs;
    private static final String PREF_SERVER_IP = "server_ip";
    private static final String DEFAULT_IP = "192.168.42.129:8000";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // تمام‌صفحه و روشن ماندن دائمی صفحه نمایش
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        setImmersiveMode();

        webView = new WebView(this);
        setContentView(webView);

        prefs = getSharedPreferences("GalamNooriPrefs", Context.MODE_PRIVATE);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(false);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setLoadsImagesAutomatically(true);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        webView.setWebViewClient(new WebViewClient());

        // بررسی آدرس ذخیره شده یا درخواست آدرس سرور
        String serverIp = prefs.getString(PREF_SERVER_IP, "");
        if (serverIp.isEmpty()) {
            promptServerIp();
        } else {
            loadServer(serverIp);
        }

        // کلیک طولانی برای باز کردن منوی تغییر آی‌پی
        webView.setOnLongClickListener(v -> {
            promptServerIp();
            return true;
        });
    }

    private void promptServerIp() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("آدرس سرور کامپیوتر");
        builder.setMessage("آدرس نمایش داده شده در نرم‌افزار کامپیوتر را وارد کنید:\n(برای کابل USB معمولاً 192.168.42.129:8000 یا IP شبکه است)");

        final EditText input = new EditText(this);
        input.setHint(DEFAULT_IP);
        String current = prefs.getString(PREF_SERVER_IP, DEFAULT_IP);
        input.setText(current);
        builder.setView(input);

        builder.setPositiveButton("اتصال", (dialog, which) -> {
            String ip = input.getText().toString().trim();
            if (ip.isEmpty()) ip = DEFAULT_IP;
            prefs.edit().putString(PREF_SERVER_IP, ip).apply();
            loadServer(ip);
        });

        builder.setNegativeButton("انصراف", (dialog, which) -> dialog.cancel());
        builder.show();
    }

    private void loadServer(String ipOrUrl) {
        if (!ipOrUrl.startsWith("http://") && !ipOrUrl.startsWith("https://")) {
            ipOrUrl = "http://" + ipOrUrl;
        }
        webView.loadUrl(ipOrUrl);
    }

    private void setImmersiveMode() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            );
        }
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            setImmersiveMode();
        }
    }

    @Override
    public void onBackPressed() {
        promptServerIp();
    }
}

