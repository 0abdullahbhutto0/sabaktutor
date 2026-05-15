import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, SafeAreaView } from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialIcons } from '@expo/vector-icons';

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
        {/* Node 1: Completed */}
        <View style={[styles.nodeContainer, { alignItems: 'center' }]}>
          <TouchableOpacity activeOpacity={0.7} style={styles.nodeCompleted} onPress={() => router.push('/quiz/ch1')}>
            <MaterialIcons name="check-circle" size={48} color="#ffffff" />
          </TouchableOpacity>
          <View style={styles.nodeLabelCompleted}>
            <Text style={styles.nodeLabelTextCompleted}>Ch 1: Fundamentals</Text>
          </View>
        </View>

        {/* Node 2: Locked */}
        <View style={[styles.nodeContainer, { alignItems: 'flex-end', paddingRight: 40, marginTop: -20 }]}>
          <View style={styles.nodeLocked}>
            <MaterialIcons name="lock" size={40} color="#bbcbbb" />
          </View>
          <View style={styles.nodeLabelLocked}>
            <Text style={styles.nodeLabelTextLocked}>Ch 2: Operating System</Text>
          </View>
        </View>

        {/* Node 3: Locked */}
        <View style={[styles.nodeContainer, { alignItems: 'flex-start', paddingLeft: 40, marginTop: -20 }]}>
          <View style={styles.nodeLocked}>
            <MaterialIcons name="lock" size={40} color="#bbcbbb" />
          </View>
          <View style={styles.nodeLabelLocked}>
            <Text style={styles.nodeLabelTextLocked}>Ch 3: Office Automation</Text>
          </View>
        </View>

        {/* Node 4: Locked */}
        <View style={[styles.nodeContainer, { alignItems: 'center', marginTop: -20 }]}>
          <View style={styles.nodeLocked}>
            <MaterialIcons name="lock" size={40} color="#bbcbbb" />
          </View>
          <View style={styles.nodeLabelLocked}>
            <Text style={styles.nodeLabelTextLocked}>Ch 4: Data Communication</Text>
          </View>
        </View>

        {/* Node 5: Locked */}
        <View style={[styles.nodeContainer, { alignItems: 'flex-end', paddingRight: 40, marginTop: -20 }]}>
          <View style={styles.nodeLocked}>
            <MaterialIcons name="lock" size={40} color="#bbcbbb" />
          </View>
          <View style={styles.nodeLabelLocked}>
            <Text style={styles.nodeLabelTextLocked}>Ch 5: Computer Networks</Text>
          </View>
        </View>
      </ScrollView>
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
    position: 'relative',
    marginBottom: 20,
  },
  nodeCompleted: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#2ecc71',
    borderWidth: 4,
    borderColor: '#006d37',
    justifyContent: 'center',
    alignItems: 'center',
    borderBottomWidth: 8, // Chunky shadow effect
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
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#e3efff',
    borderWidth: 4,
    borderColor: '#bbcbbb',
    justifyContent: 'center',
    alignItems: 'center',
    opacity: 0.6,
  },
  nodeLabelLocked: {
    marginTop: 12,
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
  },
});
