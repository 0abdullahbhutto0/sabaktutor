import React, { useState, useEffect } from 'react';
import { View, Modal, StyleSheet, TouchableOpacity, Text, ActivityIndicator, SafeAreaView, Platform } from 'react-native';
import { WebView } from 'react-native-webview';
import { MaterialIcons } from '@expo/vector-icons';
import { Asset } from 'expo-asset';
import * as FileSystem from 'expo-file-system/legacy';
import ChunkyButton from './ChunkyButton';

type Props = {
  visible: boolean;
  onClose: () => void;
  onInsert: (latex: string) => void;
  initialLatex?: string;
};

export function MathInputModal({ visible, onClose, onInsert, initialLatex = '' }: Props) {
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const webviewRef = React.useRef<WebView>(null);

  useEffect(() => {
    if (visible && !htmlContent) {
      loadMathLive();
    }
  }, [visible]);

  const loadMathLive = async () => {
    try {
      setLoading(true);
      // Load the bundled mathlive script
      const [asset] = await Asset.loadAsync(require('../../assets/mathlive_bundle.txt'));
      
      let scriptStr = '';
      if (asset.localUri) {
        scriptStr = await FileSystem.readAsStringAsync(asset.localUri);
      } else {
        // Fallback for some environments where localUri isn't immediately ready
        const download = await FileSystem.downloadAsync(asset.uri, FileSystem.documentDirectory + 'mathlive.js');
        scriptStr = await FileSystem.readAsStringAsync(download.uri);
      }

      const html = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0, viewport-fit=cover">
          <style>
            body { 
              margin: 0; 
              display: flex; 
              flex-direction: column;
              height: 100vh; 
              background-color: #0F172A; 
              color: white; 
              font-family: system-ui, sans-serif;
            }
            .editor-container {
              flex: 1;
              display: flex;
              align-items: center;
              justify-content: center;
              padding: 20px;
            }
            math-field { 
              font-size: 28px; 
              width: 100%; 
              padding: 16px;
              border: 2px solid #334155; 
              border-radius: 12px;
              background: #1E293B; 
              color: white; 
              min-height: 80px;
            }
            math-field::part(virtual-keyboard-toggle) { 
              display: none; 
            }
          </style>
          <script>
            ${scriptStr}
          </script>
        </head>
        <body>
          <div class="editor-container">
            <math-field id="mf">${initialLatex.replace(/\\/g, '\\\\')}</math-field>
          </div>
          <script>
            const mf = document.getElementById('mf');
            
            // Force focus to show virtual keyboard
            setTimeout(() => {
              mf.focus();
              mathVirtualKeyboard.show();
            }, 500);

            // Listen to messages from React Native
            document.addEventListener('message', function(event) {
              const data = JSON.parse(event.data);
              if (data.type === 'get_value') {
                window.ReactNativeWebView.postMessage(JSON.stringify({
                  type: 'value',
                  latex: mf.value
                }));
              }
            });
            window.addEventListener('message', function(event) {
              const data = JSON.parse(event.data);
              if (data.type === 'get_value') {
                window.ReactNativeWebView.postMessage(JSON.stringify({
                  type: 'value',
                  latex: mf.value
                }));
              }
            });
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

  const handleInsert = () => {
    // Request value from webview
    if (webviewRef.current) {
      const script = `
        window.ReactNativeWebView.postMessage(JSON.stringify({
          type: 'value',
          latex: document.getElementById('mf').value
        }));
        true;
      `;
      webviewRef.current.injectJavaScript(script);
    }
  };

  const onMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'value') {
        onInsert(data.latex);
      }
    } catch(e) {}
  };

  return (
    <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={onClose}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={onClose} style={styles.iconButton}>
            <MaterialIcons name="close" size={28} color="#94A3B8" />
          </TouchableOpacity>
          <Text style={styles.title}>Math Editor</Text>
          <TouchableOpacity onPress={handleInsert} style={styles.iconButton}>
            <MaterialIcons name="check" size={28} color="#4ADE80" />
          </TouchableOpacity>
        </View>

        <View style={styles.webviewContainer}>
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#3B82F6" />
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
            />
          )}
        </View>
        
        <View style={styles.bottomBar}>
          <ChunkyButton 
            title="Insert Equation" 
            onPress={handleInsert} 
            style={{ width: '100%' }}
            color="#3B82F6"
          />
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0F172A',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1E293B',
    backgroundColor: '#0F172A',
  },
  iconButton: {
    padding: 8,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#FFF',
  },
  webviewContainer: {
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
    marginTop: 16,
    fontSize: 16,
  },
  webview: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  bottomBar: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#1E293B',
    backgroundColor: '#0F172A',
  }
});
