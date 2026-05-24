import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TextInput, TouchableOpacity, ScrollView, Platform, KeyboardAvoidingView, StatusBar } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, Easing, withSequence, useAnimatedProps } from 'react-native-reanimated';
import Svg, { Rect } from 'react-native-svg';
import { MaterialIcons } from '@expo/vector-icons';
import auth from '@react-native-firebase/auth';
import { BACKEND_URL } from './services/quizService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatSession {
  messages: Message[];
  previousSummary: string;
}

export const chatSessionStore: Record<string, ChatSession> = {};

const ACTION_WORDS = [
  "Pondering the universe...",
  "Thinking quietly...",
  "Flipping through the textbook...",
  "Consulting the archives...",
  "Connecting the dots..."
];

const FormattedText = ({ text, textStyle }: { text: string, textStyle: any }) => {
  const lines = text.split('\n');
  return (
    <View>
      {lines.map((line, i) => {
        const isBullet = line.trim().startsWith('- ') || line.trim().startsWith('* ');
        const isNumbered = /^\d+\.\s/.test(line.trim());
        const isQuote = line.trim().startsWith('>');
        
        // Remove markdown list chars for rendering
        let cleanLine = line;
        if (isBullet) cleanLine = cleanLine.replace(/^[-*]\s/, '');
        if (isNumbered) cleanLine = cleanLine.replace(/^\d+\.\s/, '');
        if (isQuote) cleanLine = cleanLine.replace(/^>\s*/, '');
        
        // Parse bold text
        const parts = cleanLine.split(/(\*\*.*?\*\*)/g);
        
        return (
          <View key={i} style={{ flexDirection: 'row', marginBottom: line.trim() === '' ? 8 : 2, paddingLeft: isBullet || isNumbered || isQuote ? 16 : 0, borderLeftWidth: isQuote ? 2 : 0, borderLeftColor: isQuote ? '#3B82F6' : 'transparent' }}>
            {isBullet && <Text style={[textStyle, { marginRight: 8 }]}>•</Text>}
            {isNumbered && <Text style={[textStyle, { marginRight: 8 }]}>{line.trim().match(/^\d+\.\s/)?.[0]}</Text>}
            
            <Text style={[textStyle, isQuote && { fontStyle: 'italic', color: '#94A3B8' }, { flexShrink: 1 }]}>
              {parts.map((p, j) => {
                if (p.startsWith('**') && p.endsWith('**')) {
                  return <Text key={j} style={{ fontWeight: 'bold', color: textStyle.color === '#FFFFFF' ? '#FFFFFF' : '#60A5FA' }}>{p.slice(2, -2)}</Text>;
                }
                return p;
              })}
            </Text>
          </View>
        );
      })}
    </View>
  );
};

const AnimatedRect = Animated.createAnimatedComponent(Rect);

const BouncingDots = () => {
  const dot1 = useSharedValue(0);
  const dot2 = useSharedValue(0);
  const dot3 = useSharedValue(0);

  useEffect(() => {
    const bounce = (val: any, delay: number) => {
      setTimeout(() => {
        val.value = withRepeat(
          withSequence(
            withTiming(-4, { duration: 300, easing: Easing.out(Easing.ease) }),
            withTiming(0, { duration: 300, easing: Easing.in(Easing.ease) })
          ),
          -1,
          true
        );
      }, delay);
    };
    bounce(dot1, 0);
    bounce(dot2, 150);
    bounce(dot3, 300);
  }, []);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'flex-end', marginLeft: 2, paddingBottom: 2 }}>
      <Animated.Text style={[{ color: '#3B82F6', fontSize: 16, fontWeight: 'bold' }, useAnimatedStyle(() => ({ transform: [{ translateY: dot1.value }] }))]}>.</Animated.Text>
      <Animated.Text style={[{ color: '#3B82F6', fontSize: 16, fontWeight: 'bold' }, useAnimatedStyle(() => ({ transform: [{ translateY: dot2.value }] }))]}>.</Animated.Text>
      <Animated.Text style={[{ color: '#3B82F6', fontSize: 16, fontWeight: 'bold' }, useAnimatedStyle(() => ({ transform: [{ translateY: dot3.value }] }))]}>.</Animated.Text>
    </View>
  );
};

const TypingBubble = ({ actionWord }: { actionWord: string }) => {
  const dashOffset = useSharedValue(0);
  
  useEffect(() => {
    dashOffset.value = withRepeat(
      withTiming(-20, { duration: 500, easing: Easing.linear }),
      -1,
      false
    );
  }, []);

  const animatedProps = useAnimatedProps(() => {
    return {
      strokeDashoffset: dashOffset.value
    };
  });

  return (
    <View style={[styles.messageBubble, styles.messageAssistant, { overflow: 'hidden', position: 'relative', borderWidth: 0, paddingHorizontal: 0, paddingVertical: 0 }]}>
      <View style={StyleSheet.absoluteFill}>
        <Svg width="100%" height="100%">
          <AnimatedRect 
            x="0" y="0" 
            width="100%" height="100%" 
            rx="20" ry="20" 
            stroke="#3B82F6" 
            strokeWidth="4" 
            fill="transparent" 
            strokeDasharray="8, 8" 
            animatedProps={animatedProps} 
          />
        </Svg>
      </View>
      <View style={{ paddingHorizontal: 16, paddingVertical: 12, flexDirection: 'row', alignItems: 'center' }}>
        <Text style={[styles.typingText]}>{actionWord}</Text>
        <BouncingDots />
      </View>
    </View>
  );
};

export default function ChatScreen() {
  const router = useRouter();
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  const book = subjectStr === 'physics' ? 'phy_9' : 'cs_9';
  const insets = useSafeAreaInsets();
  
  const userId = auth().currentUser?.uid || 'guest';
  const sessionKey = `${userId}_${book}`;
  
  const [messages, setMessages] = useState<Message[]>(
    chatSessionStore[sessionKey]?.messages || [
      { id: 'initial', role: 'assistant', content: `Hello! I'm your SabakTutor study buddy for ${subjectStr === 'physics' ? 'Physics' : 'Computer Science'}. What would you like to learn today?` }
    ]
  );
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [actionWord, setActionWord] = useState(ACTION_WORDS[0]);
  const [previousSummary, setPreviousSummary] = useState<string>(chatSessionStore[sessionKey]?.previousSummary || '');
  
  const scrollViewRef = useRef<ScrollView>(null);
  const actionWordInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    chatSessionStore[sessionKey] = { messages, previousSummary };
  }, [messages, previousSummary, sessionKey]);

  useEffect(() => {
    if (isTyping) {
      actionWordInterval.current = setInterval(() => {
        setActionWord(ACTION_WORDS[Math.floor(Math.random() * ACTION_WORDS.length)]);
      }, 2000);
    } else {
      if (actionWordInterval.current) clearInterval(actionWordInterval.current);
    }
    return () => {
      if (actionWordInterval.current) clearInterval(actionWordInterval.current);
    };
  }, [isTyping]);

  const requestSummaryIfNeeded = async (currentMessages: Message[]) => {
    // Only send the last 5 messages to the API. If we have more than 7 total (including initial), summarize.
    if (currentMessages.length > 7) {
      const messagesToSummarize = currentMessages.slice(1, currentMessages.length - 5);
      if (messagesToSummarize.length > 0) {
        try {
          const res = await fetch(`${BACKEND_URL}/ask/summarize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              history: messagesToSummarize.map(m => ({ role: m.role, content: m.content }))
            })
          });
          const data = await res.json();
          if (data.summary) {
            setPreviousSummary(data.summary);
          }
        } catch (e) {
          console.error("Failed to summarize history:", e);
        }
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: input.trim() };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput('');
    setIsTyping(true);
    setActionWord(ACTION_WORDS[Math.floor(Math.random() * ACTION_WORDS.length)]);
    
    // Request summary in background if needed
    requestSummaryIfNeeded(newMessages);

    // Prepare history (last 5 messages only)
    const historyToSend = newMessages.slice(-5).slice(0, -1); // exclude the current user message from history array, since it goes in 'query'
    
    const assistantMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '' }]);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BACKEND_URL}/ask/stream`, true);
    xhr.setRequestHeader('Content-Type', 'application/json');
    
    let lastProcessedIndex = 0;
    
    xhr.onprogress = () => {
      const newText = xhr.responseText.substring(lastProcessedIndex);
      const lines = newText.split('\n');
      
      let newTokens = "";
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const dataStr = line.substring(6);
            if (dataStr === '[DONE]') continue;
            
            const data = JSON.parse(dataStr);
            if (data && data.token) {
              newTokens += data.token;
            }
          } catch (e) {
            // Wait for full chunk
          }
        }
      }
      
      if (newTokens) {
        setMessages(prev => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg.role === 'assistant') {
            lastMsg.content += newTokens;
          }
          return updated;
        });
        
        // Update processed index (only counting full lines processed to avoid cutting JSON in half)
        const lastNewLine = xhr.responseText.lastIndexOf('\n');
        if (lastNewLine > lastProcessedIndex) {
          lastProcessedIndex = lastNewLine + 1;
        }
      }
    };
    
    xhr.onload = () => {
      setIsTyping(false);
      if (xhr.status !== 200) {
        setMessages(prev => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          if (lastMsg.role === 'assistant' && !lastMsg.content) {
            lastMsg.content = `Server error ${xhr.status}: ${xhr.responseText}`;
          }
          return updated;
        });
      }
    };
    
    xhr.onerror = (e) => {
      setIsTyping(false);
      setMessages(prev => {
        const updated = [...prev];
        const lastMsg = updated[updated.length - 1];
        if (lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = `Network error! Tried to connect to ${BACKEND_URL}. Please check if your PC's IP address has changed in quizService.ts.`;
        }
        return updated;
      });
    };
    
    xhr.send(JSON.stringify({
      book_id: book,
      query: userMsg.content,
      history: historyToSend.map(m => ({ role: m.role, content: m.content })),
      previous_summary: previousSummary || null
    }));
  };

  const handleNewChat = () => {
    const initial: Message[] = [
      { id: Date.now().toString(), role: 'assistant', content: `Hello! I'm your SabakTutor study buddy for ${subjectStr === 'physics' ? 'Physics' : 'Computer Science'}. What would you like to learn today?` }
    ];
    setMessages(initial);
    setPreviousSummary('');
    setInput('');
    chatSessionStore[sessionKey] = { messages: initial, previousSummary: '' };
  };

  return (
    <SafeAreaView style={[styles.safeArea, { paddingTop: insets.top }]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialIcons name="arrow-back" size={24} color="#94A3B8" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Study Buddy</Text>
        <TouchableOpacity onPress={handleNewChat} style={styles.backButton}>
          <MaterialIcons name="refresh" size={24} color="#94A3B8" />
        </TouchableOpacity>
      </View>

      <KeyboardAvoidingView 
        style={styles.container} 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        <ScrollView 
          ref={scrollViewRef}
          contentContainerStyle={styles.scrollContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((msg, idx) => (
            <View 
              key={msg.id} 
              style={[
                styles.messageWrapper, 
                msg.role === 'user' ? styles.messageWrapperUser : styles.messageWrapperAssistant
              ]}
            >
              {msg.role === 'assistant' && (
                <View style={styles.avatarAssistant}>
                  <MaterialIcons name="smart-toy" size={20} color="#FFF" />
                </View>
              )}
              
              {msg.role === 'assistant' && !msg.content && isTyping && idx === messages.length - 1 ? (
                <TypingBubble actionWord={actionWord} />
              ) : (
                <View 
                  style={[
                    styles.messageBubble,
                    msg.role === 'user' ? styles.messageUser : styles.messageAssistant,
                  ]}
                >
                  <FormattedText 
                    text={msg.content} 
                    textStyle={[styles.messageText, msg.role === 'user' ? styles.messageTextUser : styles.messageTextAssistant]} 
                  />
                </View>
              )}
              
              {msg.role === 'user' && (
                <View style={styles.avatarUser}>
                  <MaterialIcons name="person" size={20} color="#FFF" />
                </View>
              )}
            </View>
          ))}
        </ScrollView>

        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            placeholder="Ask a question about the syllabus..."
            placeholderTextColor="#64748B"
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={500}
            editable={!isTyping}
          />
          <TouchableOpacity 
            style={[styles.sendButton, (!input.trim() || isTyping) && styles.sendButtonDisabled]} 
            onPress={handleSend}
            disabled={!input.trim() || isTyping}
          >
            <MaterialIcons name="send" size={24} color="#FFF" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F172A',
    paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight : 0,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: '#1E293B',
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    color: '#F8FAFC',
    fontSize: 20,
    fontWeight: 'bold',
  },
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
    gap: 16,
  },
  messageWrapper: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 8,
    gap: 8,
  },
  messageWrapperUser: {
    justifyContent: 'flex-end',
  },
  messageWrapperAssistant: {
    justifyContent: 'flex-start',
  },
  avatarAssistant: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarUser: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#10B981',
    justifyContent: 'center',
    alignItems: 'center',
  },
  messageBubble: {
    maxWidth: '75%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
  },
  messageAssistant: {
    backgroundColor: '#1E293B',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#334155',
  },
  messageUser: {
    backgroundColor: '#10B981',
    borderBottomRightRadius: 4,
  },
  messageTyping: {
    backgroundColor: 'transparent',
    borderColor: '#3B82F6',
    borderStyle: 'dashed',
  },
  messageText: {
    fontSize: 16,
    lineHeight: 24,
  },
  messageTextAssistant: {
    color: '#F8FAFC',
  },
  messageTextUser: {
    color: '#FFFFFF',
    fontWeight: '500',
  },
  typingText: {
    color: '#3B82F6',
    fontStyle: 'italic',
    fontSize: 14,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#1E293B',
    borderTopWidth: 1,
    borderTopColor: '#334155',
    alignItems: 'flex-end',
    gap: 12,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#0F172A',
    color: '#F8FAFC',
    borderRadius: 24,
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 12,
    fontSize: 16,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: '#334155',
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#3B82F6',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 2,
  },
  sendButtonDisabled: {
    backgroundColor: '#334155',
  }
});
