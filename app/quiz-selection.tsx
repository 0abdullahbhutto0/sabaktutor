import React, { useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView, Pressable, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import Svg, { Path } from 'react-native-svg';
import { preloadNextQuizzes } from './services/quizService';
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

  const [progress, setProgress] = React.useState<Record<string, boolean>>({});
  const [masteryPoints, setMasteryPoints] = React.useState<number>(0);

  useEffect(() => {
    preloadNextQuizzes(0);
    
    const user = auth().currentUser;
    if (!user) return;

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
  }, []);

  const levels = ['ch1', 'ch2', 'ch3', 'ch4', 'ch5'];
  
  // A level is completed if it's in progress.
  // A level is unlocked if it's ch1, or the previous level is completed.
  const isCompleted = (levelId: string) => !!progress[levelId];
  const isUnlocked = (index: number) => index === 0 || isCompleted(levels[index - 1]);

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
        <View style={{ width: MAP_WIDTH, height: 600, alignSelf: 'center', position: 'relative' }}>
          {/* Dashed Path (SVG) */}
          <Svg height="600" width={MAP_WIDTH} style={{ position: 'absolute', top: NODE_SIZE / 2, left: 0 }}>
            {/* Center to Right (ch1 to ch2) */}
            <Path 
              d={`M ${CENTER_X} 0 C ${CENTER_X} 50, ${RIGHT_X} 50, ${RIGHT_X} 120`}
              stroke={isUnlocked(1) ? "#006d37" : "#bbcbbb"} 
              strokeWidth={isUnlocked(1) ? "6" : "4"} 
              strokeDasharray={isUnlocked(1) ? "" : "8 8"} 
              fill="none"
            />
            {/* Right to Center (ch2 to ch3) */}
            <Path 
              d={`M ${RIGHT_X} 120 C ${RIGHT_X} 180, ${CENTER_X} 180, ${CENTER_X} 240`}
              stroke={isUnlocked(2) ? "#006d37" : "#bbcbbb"} 
              strokeWidth={isUnlocked(2) ? "6" : "4"} 
              strokeDasharray={isUnlocked(2) ? "" : "8 8"} 
              fill="none"
            />
            {/* Center to Left (ch3 to ch4) */}
            <Path 
              d={`M ${CENTER_X} 240 C ${CENTER_X} 300, ${LEFT_X} 300, ${LEFT_X} 360`}
              stroke={isUnlocked(3) ? "#006d37" : "#bbcbbb"} 
              strokeWidth={isUnlocked(3) ? "6" : "4"} 
              strokeDasharray={isUnlocked(3) ? "" : "8 8"} 
              fill="none"
            />
            {/* Left to Center (ch4 to ch5) */}
            <Path 
              d={`M ${LEFT_X} 360 C ${LEFT_X} 420, ${CENTER_X} 420, ${CENTER_X} 480`}
              stroke={isUnlocked(4) ? "#006d37" : "#bbcbbb"} 
              strokeWidth={isUnlocked(4) ? "6" : "4"} 
              strokeDasharray={isUnlocked(4) ? "" : "8 8"} 
              fill="none"
            />
          </Svg>

          {/* Node 1 */}
          <View style={[styles.nodeContainer, { left: CENTER_X - NODE_SIZE/2, top: 0 }]}>
            <Pressable 
              style={({ pressed }) => [
                isCompleted('ch1') ? styles.nodeCompleted : styles.nodeUnlocked, 
                pressed && styles.nodePressed
              ]} 
              onPress={() => router.push('/quiz/ch1')}
            >
              {isCompleted('ch1') ? (
                <MaterialIcons name="check-circle" size={48} color="#ffffff" />
              ) : (
                <MaterialIcons name="play-arrow" size={48} color="#ffffff" />
              )}
            </Pressable>
            <View style={isCompleted('ch1') ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
              <Text style={isCompleted('ch1') ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>Ch 1: Fundamentals</Text>
            </View>
          </View>

          {/* Node 2 */}
          <View style={[styles.nodeContainer, { left: RIGHT_X - NODE_SIZE/2, top: 120 }]}>
            <Pressable 
              style={({ pressed }) => [
                !isUnlocked(1) ? styles.nodeLocked : isCompleted('ch2') ? styles.nodeCompleted : styles.nodeUnlocked,
                isUnlocked(1) && pressed && styles.nodePressed
              ]}
              onPress={() => isUnlocked(1) && router.push('/quiz/ch2')}
            >
              {!isUnlocked(1) ? (
                <MaterialIcons name="lock" size={40} color="#bbcbbb" />
              ) : isCompleted('ch2') ? (
                <MaterialIcons name="check-circle" size={48} color="#ffffff" />
              ) : (
                <MaterialIcons name="play-arrow" size={48} color="#ffffff" />
              )}
            </Pressable>
            <View style={!isUnlocked(1) ? styles.nodeLabelLocked : isCompleted('ch2') ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
              <Text style={!isUnlocked(1) ? styles.nodeLabelTextLocked : isCompleted('ch2') ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>Ch 2: Operating System</Text>
            </View>
          </View>

          {/* Node 3 */}
          <View style={[styles.nodeContainer, { left: CENTER_X - NODE_SIZE/2, top: 240 }]}>
            <Pressable 
              style={({ pressed }) => [
                !isUnlocked(2) ? styles.nodeLocked : isCompleted('ch3') ? styles.nodeCompleted : styles.nodeUnlocked,
                isUnlocked(2) && pressed && styles.nodePressed
              ]}
              onPress={() => isUnlocked(2) && router.push('/quiz/ch3')}
            >
              {!isUnlocked(2) ? (
                <MaterialIcons name="lock" size={40} color="#bbcbbb" />
              ) : isCompleted('ch3') ? (
                <MaterialIcons name="check-circle" size={48} color="#ffffff" />
              ) : (
                <MaterialIcons name="play-arrow" size={48} color="#ffffff" />
              )}
            </Pressable>
            <View style={!isUnlocked(2) ? styles.nodeLabelLocked : isCompleted('ch3') ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
              <Text style={!isUnlocked(2) ? styles.nodeLabelTextLocked : isCompleted('ch3') ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>Ch 3: Office Automation</Text>
            </View>
          </View>

          {/* Node 4 */}
          <View style={[styles.nodeContainer, { left: LEFT_X - NODE_SIZE/2, top: 360 }]}>
            <Pressable 
              style={({ pressed }) => [
                !isUnlocked(3) ? styles.nodeLocked : isCompleted('ch4') ? styles.nodeCompleted : styles.nodeUnlocked,
                isUnlocked(3) && pressed && styles.nodePressed
              ]}
              onPress={() => isUnlocked(3) && router.push('/quiz/ch4')}
            >
              {!isUnlocked(3) ? (
                <MaterialIcons name="lock" size={40} color="#bbcbbb" />
              ) : isCompleted('ch4') ? (
                <MaterialIcons name="check-circle" size={48} color="#ffffff" />
              ) : (
                <MaterialIcons name="play-arrow" size={48} color="#ffffff" />
              )}
            </Pressable>
            <View style={!isUnlocked(3) ? styles.nodeLabelLocked : isCompleted('ch4') ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
              <Text style={!isUnlocked(3) ? styles.nodeLabelTextLocked : isCompleted('ch4') ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>Ch 4: Data Communication</Text>
            </View>
          </View>

          {/* Node 5 */}
          <View style={[styles.nodeContainer, { left: CENTER_X - NODE_SIZE/2, top: 480 }]}>
            <Pressable 
              style={({ pressed }) => [
                !isUnlocked(4) ? styles.nodeLocked : isCompleted('ch5') ? styles.nodeCompleted : styles.nodeUnlocked,
                isUnlocked(4) && pressed && styles.nodePressed
              ]}
              onPress={() => isUnlocked(4) && router.push('/quiz/ch5')}
            >
              {!isUnlocked(4) ? (
                <MaterialIcons name="lock" size={40} color="#bbcbbb" />
              ) : isCompleted('ch5') ? (
                <MaterialIcons name="check-circle" size={48} color="#ffffff" />
              ) : (
                <MaterialIcons name="play-arrow" size={48} color="#ffffff" />
              )}
            </Pressable>
            <View style={!isUnlocked(4) ? styles.nodeLabelLocked : isCompleted('ch5') ? styles.nodeLabelCompleted : styles.nodeLabelUnlocked}>
              <Text style={!isUnlocked(4) ? styles.nodeLabelTextLocked : isCompleted('ch5') ? styles.nodeLabelTextCompleted : styles.nodeLabelTextUnlocked}>Ch 5: Computer Networks</Text>
            </View>
          </View>
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

        <TouchableOpacity style={styles.navItem} onPress={() => router.replace('/profile')}>
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
