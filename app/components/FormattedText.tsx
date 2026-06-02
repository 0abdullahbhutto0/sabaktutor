import React from 'react';
import { View, Platform, Text, Dimensions } from 'react-native';
import Markdown from 'react-native-markdown-display';
import { MathJaxSvg } from 'react-native-mathjax-html-to-svg';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

/**
 * Splits text into segments of plain text and math expressions.
 * Returns an array of { type: 'text' | 'math', content: string, display: boolean }
 */
function splitTextAndMath(text: string) {
  // Match $$...$$, \[...\] (display) and $...$ , \(...\) (inline)
  const mathRegex = /(\$\$[\s\S]*?\$\$|\\\[[\s\S]*?\\\]|\$[\s\S]*?\$|\\\([\s\S]*?\\\))/g;
  const parts = text.split(mathRegex);

  return parts
    .filter(p => p !== '' && p != null)
    .map(part => {
      const isDisplayMath = part.startsWith('$$') || part.startsWith('\\[');
      const isInlineMath = (part.startsWith('$') && !part.startsWith('$$')) || part.startsWith('\\(');

      if (isDisplayMath || isInlineMath) {
        return { type: 'math' as const, content: part, display: isDisplayMath };
      }
      return { type: 'text' as const, content: part, display: false };
    });
}

function getMarkdownStyles(textStyle: any) {
  const color = textStyle?.color || '#FFF';
  const fontSize = textStyle?.fontSize || 16;
  const textAlign = textStyle?.textAlign || 'auto';
  
  return {
    body: { 
      margin: 0, 
      color,
      fontSize,
      textAlign,
    },
    text: { color, textAlign },
    heading1: { fontSize: 24, fontWeight: 'bold' as const, marginVertical: 8, color, textAlign },
    heading2: { fontSize: 20, fontWeight: 'bold' as const, marginVertical: 6, color, textAlign },
    heading3: { fontSize: 18, fontWeight: 'bold' as const, marginVertical: 4, color, textAlign },
    paragraph: { 
      fontSize, 
      marginTop: 4, 
      marginBottom: 4, 
      color,
      textAlign,
      lineHeight: textStyle?.lineHeight || fontSize * 1.5,
    },
    list_item: { fontSize, marginVertical: 2, color },
    bullet_list: { marginVertical: 4 },
    ordered_list: { marginVertical: 4 },
    strong: { fontWeight: 'bold' as const, color: color === '#FFFFFF' || color === '#FFF' ? '#FFFFFF' : '#60A5FA' },
    em: { fontStyle: 'italic' as const, color },
    code_inline: { 
      backgroundColor: 'rgba(255,255,255,0.1)', 
      color, 
      paddingHorizontal: 4, 
      borderRadius: 4, 
      fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' 
    },
    code_block: { 
      backgroundColor: 'rgba(0,0,0,0.2)', 
      color, 
      padding: 8, 
      borderRadius: 8, 
      fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace', 
      marginVertical: 8 
    },
    fence: { 
      backgroundColor: 'rgba(0,0,0,0.2)', 
      color, 
      padding: 8, 
      borderRadius: 8, 
      fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace', 
      marginVertical: 8 
    },
    blockquote: { 
      backgroundColor: 'transparent',
      borderLeftWidth: 0, 
      paddingLeft: 0, 
      fontStyle: 'normal' as const, 
      opacity: 1, 
      color 
    },
  };
}

export const FormattedText = ({ text, textStyle }: { text: string; textStyle: any }) => {
  if (!text) return null;

  // Normalize textStyle to a plain object (handles arrays from StyleSheet)
  const flatStyle = Array.isArray(textStyle)
    ? Object.assign({}, ...textStyle.filter(Boolean))
    : (textStyle || {});

  const segments = splitTextAndMath(text);
  const hasMath = segments.some(s => s.type === 'math');

  // Fast path: no math at all, just render pure Markdown
  if (!hasMath) {
    return (
      <View style={{ width: '100%' }}>
        <Markdown style={getMarkdownStyles(flatStyle)}>
          {text}
        </Markdown>
      </View>
    );
  }

  const isCentered = flatStyle.textAlign === 'center';

  // Render segments: text parts via Markdown, math parts via MathJaxSvg
  return (
    <View style={{ width: '100%', alignItems: isCentered ? 'center' : undefined }}>
      {segments.map((seg, index) => {
        if (seg.type === 'math') {
          if (seg.display) {
            // Display math: centered, full-width block
            return (
              <View 
                key={`math-${index}`} 
                style={{ 
                  width: '100%', 
                  alignItems: 'center', 
                  marginVertical: 8,
                  overflow: 'hidden',
                }}
              >
                <MathJaxSvg
                  fontSize={flatStyle.fontSize || 16}
                  color={flatStyle.color || '#fff'}
                  fontCache={true}
                >
                  {seg.content}
                </MathJaxSvg>
              </View>
            );
          } else {
            // Inline math: compact, left-aligned by default
            return (
              <View 
                key={`math-${index}`} 
                style={{ 
                  alignSelf: flatStyle.textAlign === 'center' ? 'center' : 'flex-start',
                  marginVertical: 2,
                  overflow: 'hidden',
                }}
              >
                <MathJaxSvg
                  fontSize={flatStyle.fontSize || 16}
                  color={flatStyle.color || '#fff'}
                  fontCache={true}
                >
                  {seg.content}
                </MathJaxSvg>
              </View>
            );
          }
        } else {
          // Text segment: render with full Markdown support
          const trimmed = seg.content;
          if (!trimmed.trim()) return null;
          
          return (
            <View key={`text-${index}`} style={{ width: '100%' }}>
              <Markdown style={getMarkdownStyles(flatStyle)}>
                {trimmed}
              </Markdown>
            </View>
          );
        }
      })}
    </View>
  );
};
