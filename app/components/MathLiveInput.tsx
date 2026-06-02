import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ActivityIndicator, Text } from 'react-native';
import { WebView } from 'react-native-webview';
import { Asset } from 'expo-asset';
import * as FileSystem from 'expo-file-system/legacy';

type Props = {
  value: string;
  onChangeText: (text: string) => void;
};

export function MathLiveInput({ value, onChangeText }: Props) {
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const webviewRef = React.useRef<WebView>(null);

  useEffect(() => {
    if (!htmlContent) {
      loadMathLive();
    }
  }, []);

  const loadMathLive = async () => {
    try {
      setLoading(true);
      const [asset] = await Asset.loadAsync(require('../../assets/mathlive_bundle.txt'));
      
      let scriptStr = '';
      if (asset.localUri) {
        scriptStr = await FileSystem.readAsStringAsync(asset.localUri);
      } else {
        const download = await FileSystem.downloadAsync(asset.uri, FileSystem.documentDirectory + 'mathlive.js');
        scriptStr = await FileSystem.readAsStringAsync(download.uri);
      }

      const html = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0, viewport-fit=cover">
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            html, body { 
              height: 100%; 
              width: 100%;
              overflow: hidden;
              background-color: #0F172A; 
              font-family: system-ui, sans-serif;
            }
            body {
              display: flex;
              flex-direction: column;
            }
            .input-area {
              padding: 12px;
              flex-shrink: 0;
            }
            .input-area label {
              display: block;
              color: #94A3B8;
              font-size: 11px;
              font-weight: 700;
              text-transform: uppercase;
              letter-spacing: 0.5px;
              margin-bottom: 8px;
            }
            math-field { 
              font-size: 20px; 
              width: 100%; 
              padding: 14px;
              border: 2px solid #334155; 
              border-radius: 12px;
              background: #1E293B; 
              color: white; 
              min-height: 80px;
              display: block;
            }
            math-field:focus-within {
              border-color: #a855f7;
            }
            math-field::part(virtual-keyboard-toggle) { 
              color: #a855f7;
            }
          </style>
          <script>
            ${scriptStr}
          </script>
        </head>
        <body>
          <div class="input-area">
            <label>Your Answer</label>
            <math-field id="mf">${value.replace(/\\/g, '\\\\')}</math-field>
          </div>
          <script>
            const mf = document.getElementById('mf');
            
            mf.addEventListener('input', (ev) => {
              window.ReactNativeWebView.postMessage(JSON.stringify({
                type: 'value',
                latex: mf.value
              }));
            });

            // Auto-focus and show keyboard
            setTimeout(() => {
              mf.focus();
              if (typeof mathVirtualKeyboard !== 'undefined') {
                mathVirtualKeyboard.show();
              }
            }, 300);
          </script>
        </body>
        </html>
      `;
      setHtmlContent(html);
    } catch (e) {
      console.error("Failed to load MathLive:", e);
    } finally {
      setLoading(false);
    }
  };

  const onMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'value') {
        onChangeText(data.latex);
      }
    } catch(e) {}
  };

  return (
    <View style={styles.container}>
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color="#a855f7" />
          <Text style={styles.loadingText}>Loading Math Editor...</Text>
        </View>
      ) : (
        <WebView
          ref={webviewRef}
          source={{ html: htmlContent }}
          originWhitelist={['*']}
          onMessage={onMessage}
          style={styles.webview}
          keyboardDisplayRequiresUserAction={false}
          bounces={false}
          scrollEnabled={false}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    overflow: 'hidden',
  },
  webview: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#94A3B8',
    marginTop: 12,
    fontSize: 14,
  }
});
