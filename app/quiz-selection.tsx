import React, { useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView, Pressable, Dimensions } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import Svg, { Path } from 'react-native-svg';
import { preloadNextQuizzes, BOOK_CHAPTERS } from './services/quizService';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';

const { width } = Dimensions.get('window');
const MAP_WIDTH = Math.min(width - 48, 400); // Responsive max width
const CENTER_X = MAP_WIDTH / 2;
const RIGHT_X = MAP_WIDTH - 60;
const LEFT_X = 60;
const NODE_SIZE = 96;

export default function MasteryMap() {
  const router = useRouter();
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  const bookId = subjectStr === 'physics' ? 'phy_9' : 'cs_9';

  const [progress, setProgress] = React.useState<Record<string, boolean>>({});
  const [masteryPoints, setMasteryPoints] = React.useState<number>(0);
  const [userId, setUserId] = React.useState<string | null>(null);

  useEffect(() => {
    preloadNextQuizzes(0, subjectStr);
    
    const user = auth().currentUser;
    if (!user) return;
    setUserId(user.uid);

    // Listen to user progress and scores
    const unsubscribe = firestore()
      .collection('users')
      .doc(user.uid)
      .collection('progress')
      .onSnapshot((snapshot) => {
        const newProgress: Record<string, boolean> = {};
        let totalPoints = 0;
        
        snapshot.forEach(doc => {
          const data = doc.data();
          if (data.passed) {
            newProgress[doc.id] = true;
          }
          if (typeof data.score === 'number') {
            totalPoints += data.score * 10;
          }
        });
        
        setProgress(newProgress);
        setMasteryPoints(totalPoints);
      });

    return () => unsubscribe();
  }, [subjectStr]);

  const chaptersMap = BOOK_CHAPTERS[subjectStr] || BOOK_CHAPTERS['physics'];
  const chaptersCount = Object.keys(chaptersMap).length;
  
  const nodes = Array.from({ length: chaptersCount * 2 }).map((_, i) => {
    const chapterNum = Math.floor(i / 2) + 1;
    const level = `ch${chapterNum}`;
    const type = i % 2 === 0 ? 'lesson' : 'quiz';
    const title = type === 'lesson' ? `Ch ${chapterNum}: Learn` : `Ch ${chapterNum}: Test`;
    const globalId = userId ? `${type}_${userId}_${bookId}_${level}` : '';
    return { index: i, type, level, title, globalId };
  });

  const isCompleted = (globalId: string) => !!progress[globalId];
  
  const isUnlocked = (index: number) => {
    if (index === 0) return true;
    const prevNode = nodes[index - 1];
    return isCompleted(prevNode.globalId);
  };

  const getXForIndex = (index: number) => {
    const mod = index % 4;
    if (mod === 0) return CENTER_X;
    if (mod === 1) return RIGHT_X;
    if (mod === 2) return CENTER_X;
    return LEFT_X;
  };

  const getIconName = (type: string, completed: boolean) => {
    if (completed) return "check-circle";
    if (type === 'lesson') return "menu-book";
    return "star";
  };

  const renderPath = (i: number) => {
    if (i >= nodes.length - 1) return null;
    const startX = getXForIndex(i);
    const endX = getXForIndex(i + 1);
    const startY = i * 120;
    const endY = (i + 1) * 120;
    const midY = startY + 60;
    
    const unlocked = isUnlocked(i + 1);
    
    return (
      <Path 
        key={`path-${i}`}
        d={`M ${startX} ${startY} C ${startX} ${midY}, ${endX} ${midY}, ${endX} ${endY}`}
        stroke={unlocked ? "#006d37" : "#bbcbbb"} 
        strokeWidth={unlocked ? "6" : "4"} 
        strokeDasharray={unlocked ? "" : "8 8"} 
        fill="none"
      />
    );
  };

  const totalHeight = Math.max((nodes.length - 1) * 120 + NODE_SIZE, 600);

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Top App Bar */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <TouchableOpacity activeOpacity={0.7} onPress={() => router.back()}>
            <MaterialIcons name="arrow-back" size={24} color="#006d37" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>SabakTutor</Text>
        </View>
        <View style={styles.headerRight}>
          <View style={styles.energyBadge}>
            <MaterialIcons name="bolt" size={18} color="#6f5900" />
            <Text style={styles.energyText}>{masteryPoints}</Text>
          </View>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={{ width: MAP_WIDTH, height: totalHeight, alignSelf: 'center', position: 'relative' }}>
          {/* Dashed Path (SVG) */}
          <Svg height={totalHeight} width={MAP_WIDTH} style={{ position: 'absolute', top: NODE_SIZE / 2, left: 0 }}>
            {nodes.map((_, i) => renderPath(i))}
          </Svg>

          {nodes.map((node, i) => {
            const x = getXForIndex(i);
            const y = i * 120;
            const completed = isCompleted(node.globalId);
            const unlocked = isUnlocked(i);
            const iconName = getIconName(node.type, completed) as any;
            
            return (
              <View key={`node-${i}`} style={[styles.nodeContainer, { left: x - NODE_SIZE/2, top: y }]}>
                <Pressable 
                  style={({ pressed }) => [
                    !unlocked ? styles.nodeLocked : completed ? styles.nodeCompleted : styles.nodeUnlocked,
                    unlocked && pressed && styles.nodePressed
                  ]}
                  onPress={() => {
                    if (unlocked) {
                      router.push(`/${node.type}/${node.level}?subject=${subjectStr}` as any);
                    }
                  }}
                >
                  {!unlocked ? (
                    <MaterialIcons name="lock" size={40} color="#bbcbbb" />
                  ) : (
                    <MaterialIcons name={iconName} size={48} color="#ffffff" />
                  )}
                </Pressable>
                <View style={!unlocked ? styles.nodeLabelLocked : completed ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
                  <Text style={!unlocked ? styles.nodeLabelTextLocked : completed ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>{node.title}</Text>
                </View>
              </View>
            );
          })}
        </View>
      </ScrollView>

      {/* Bottom Navigation Bar */}
      <View style={styles.bottomNav}>
        <TouchableOpacity style={styles.navItem}>
          <MaterialCommunityIcons name="map-marker-path" size={28} color="#006d37" />
          <Text style={[styles.navText, { color: '#006d37' }]}>Map</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.navItem} disabled>
          <MaterialIcons name="leaderboard" size={28} color="#bbcbbb" />
          <View style={styles.comingSoonBadge}>
            <Text style={styles.comingSoonText}>SOON</Text>
          </View>
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Leaderboard</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/profile', params: { subject: subjectStr } })}>
          <MaterialIcons name="person" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Profile</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f7f9ff',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#f7f9ff',
    borderBottomWidth: 4,
    borderBottomColor: '#d1e4fb',
    paddingTop: 40, // For Android status bar
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#006d37',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  energyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fed023',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
    borderBottomWidth: 4,
    borderBottomColor: '#6f5900',
  },
  energyText: {
    color: '#6f5900',
    fontWeight: 'bold',
    fontSize: 14,
  },
  scrollContent: {
    paddingVertical: 48,
    paddingHorizontal: 24,
    gap: 48,
  },
  nodeContainer: {
    position: 'absolute',
    alignItems: 'center',
    width: NODE_SIZE,
  },
  nodeCompleted: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE/2,
    backgroundColor: '#2ecc71',
    borderWidth: 4,
    borderColor: '#006d37',
    justifyContent: 'center',
    alignItems: 'center',
    borderBottomWidth: 8, // Chunky shadow effect
  },
  nodePressed: {
    borderBottomWidth: 0,
    marginTop: 8, // Absorb the 8px bottom border difference
  },
  nodeLabelCompleted: {
    position: 'absolute',
    top: NODE_SIZE + 12,
    alignSelf: 'center',
    width: 180,
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#d1e4fb',
  },
  nodeLabelTextCompleted: {
    fontWeight: 'bold',
    fontSize: 14,
    color: '#091d2e',
    textAlign: 'center',
  },
  nodeUnlocked: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE/2,
    backgroundColor: '#3B82F6', // Blue to indicate playable
    borderWidth: 4,
    borderColor: '#1D4ED8',
    justifyContent: 'center',
    alignItems: 'center',
    borderBottomWidth: 8,
  },
  nodeLabelUnlocked: {
    position: 'absolute',
    top: NODE_SIZE + 12,
    alignSelf: 'center',
    width: 180,
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#3B82F6',
  },
  nodeLabelTextUnlocked: {
    fontWeight: 'bold',
    fontSize: 14,
    color: '#1D4ED8',
    textAlign: 'center',
  },
  nodeLocked: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE/2,
    backgroundColor: '#e3efff',
    borderWidth: 4,
    borderColor: '#bbcbbb',
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.6,
  },
  nodeLabelLocked: {
    position: 'absolute',
    top: NODE_SIZE + 12,
    alignSelf: 'center',
    width: 180,
    backgroundColor: '#d9eaff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#bbcbbb',
    opacity: 0.6,
  },
  nodeLabelTextLocked: {
    fontWeight: 'bold',
    fontSize: 14,
    color: '#3d4a3e',
    textAlign: 'center',
  },
  bottomNav: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderTopWidth: 2,
    borderTopColor: '#e3efff',
    paddingBottom: 24,
    paddingTop: 12,
    justifyContent: 'space-around',
    alignItems: 'center',
  },
  navItem: {
    alignItems: 'center',
    position: 'relative',
    flex: 1,
  },
  navText: {
    fontSize: 12,
    fontWeight: 'bold',
    marginTop: 4,
  },
  comingSoonBadge: {
    position: 'absolute',
    top: -8,
    right: 16,
    backgroundColor: '#fed023',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#6f5900',
  },
  comingSoonText: {
    fontSize: 8,
    fontWeight: '900',
    color: '#6f5900',
  },
});
