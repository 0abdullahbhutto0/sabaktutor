import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView, Pressable, Dimensions } from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import Svg, { Path, Line } from 'react-native-svg';

const { width } = Dimensions.get('window');
const MAP_WIDTH = Math.min(width - 48, 400); // Responsive max width
const CENTER_X = MAP_WIDTH / 2;
const RIGHT_X = MAP_WIDTH - 60;
const LEFT_X = 60;
const NODE_SIZE = 96;

export default function MasteryMap() {
  const router = useRouter();

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
            <Text style={styles.energyText}>1200</Text>
          </View>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={{ width: MAP_WIDTH, height: 600, alignSelf: 'center', position: 'relative' }}>
          {/* Dashed Path (SVG) */}
          <Svg height="600" width={MAP_WIDTH} style={{ position: 'absolute', top: NODE_SIZE / 2, left: 0 }}>
            {/* Center to Right */}
            <Path 
              d={`M ${CENTER_X} 0 C ${CENTER_X} 50, ${RIGHT_X} 50, ${RIGHT_X} 120`}
              stroke="#bbcbbb" strokeWidth="4" strokeDasharray="8 8" fill="none"
            />
            {/* Right to Left */}
            <Path 
              d={`M ${RIGHT_X} 120 C ${RIGHT_X} 180, ${LEFT_X} 180, ${LEFT_X} 240`}
              stroke="#bbcbbb" strokeWidth="4" strokeDasharray="8 8" fill="none"
            />
            {/* Left to Center */}
            <Path 
              d={`M ${LEFT_X} 240 C ${LEFT_X} 300, ${CENTER_X} 300, ${CENTER_X} 360`}
              stroke="#bbcbbb" strokeWidth="4" strokeDasharray="8 8" fill="none"
            />
            {/* Center to Right */}
            <Path 
              d={`M ${CENTER_X} 360 C ${CENTER_X} 420, ${RIGHT_X} 420, ${RIGHT_X} 480`}
              stroke="#bbcbbb" strokeWidth="4" strokeDasharray="8 8" fill="none"
            />
          </Svg>

          {/* Node 1: Completed */}
          <View style={[styles.nodeContainer, { left: CENTER_X - NODE_SIZE/2, top: 0 }]}>
            <Pressable 
              style={({ pressed }) => [styles.nodeCompleted, pressed && styles.nodePressed]} 
              onPress={() => router.push('/quiz/ch1')}
            >
              <MaterialIcons name="check-circle" size={48} color="#ffffff" />
            </Pressable>
            <View style={styles.nodeLabelCompleted}>
              <Text style={styles.nodeLabelTextCompleted}>Ch 1: Fundamentals</Text>
            </View>
          </View>

          {/* Node 2: Locked */}
          <View style={[styles.nodeContainer, { left: RIGHT_X - NODE_SIZE/2, top: 120 }]}>
            <View style={styles.nodeLocked}>
              <MaterialIcons name="lock" size={40} color="#bbcbbb" />
            </View>
            <View style={styles.nodeLabelLocked}>
              <Text style={styles.nodeLabelTextLocked}>Ch 2: Operating System</Text>
            </View>
          </View>

          {/* Node 3: Locked */}
          <View style={[styles.nodeContainer, { left: LEFT_X - NODE_SIZE/2, top: 240 }]}>
            <View style={styles.nodeLocked}>
              <MaterialIcons name="lock" size={40} color="#bbcbbb" />
            </View>
            <View style={styles.nodeLabelLocked}>
              <Text style={styles.nodeLabelTextLocked}>Ch 3: Office Automation</Text>
            </View>
          </View>

          {/* Node 4: Locked */}
          <View style={[styles.nodeContainer, { left: CENTER_X - NODE_SIZE/2, top: 360 }]}>
            <View style={styles.nodeLocked}>
              <MaterialIcons name="lock" size={40} color="#bbcbbb" />
            </View>
            <View style={styles.nodeLabelLocked}>
              <Text style={styles.nodeLabelTextLocked}>Ch 4: Data Communication</Text>
            </View>
          </View>

          {/* Node 5: Locked */}
          <View style={[styles.nodeContainer, { left: RIGHT_X - NODE_SIZE/2, top: 480 }]}>
            <View style={styles.nodeLocked}>
              <MaterialIcons name="lock" size={40} color="#bbcbbb" />
            </View>
            <View style={styles.nodeLabelLocked}>
              <Text style={styles.nodeLabelTextLocked}>Ch 5: Computer Networks</Text>
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

        <TouchableOpacity style={styles.navItem}>
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
    marginTop: 12,
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
    width: 160,
    alignItems: 'center',
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
