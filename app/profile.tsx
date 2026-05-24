import React from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import auth from '@react-native-firebase/auth';
import ChunkyButton from './components/ChunkyButton';

export default function Profile() {
  const router = useRouter();
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  const user = auth().currentUser;

  const handleLogout = async () => {
    try {
      await auth().signOut();
      // The _layout.tsx will automatically redirect the user to '/'
    } catch (error: any) {
      Alert.alert("Logout Error", error.message);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile</Text>
      </View>

      <View style={styles.content}>
        <View style={styles.profileCard}>
          <View style={styles.avatarPlaceholder}>
            <Text style={styles.avatarText}>{user?.email?.charAt(0).toUpperCase() || 'U'}</Text>
          </View>
          <Text style={styles.emailText}>{user?.email}</Text>
        </View>

        <View style={styles.actionContainer}>
          <TouchableOpacity style={styles.logoutButton} activeOpacity={0.7} onPress={handleLogout}>
            <MaterialIcons name="logout" size={24} color="#b91c1c" />
            <Text style={styles.logoutText}>Log Out</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Bottom Navigation Bar */}
      <View style={styles.bottomNav}>
        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/quiz-selection', params: { subject: subjectStr } })}>
          <MaterialCommunityIcons name="map-marker-path" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Map</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.navItem} onPress={() => router.replace({ pathname: '/leaderboard', params: { subject: subjectStr } })}>
          <MaterialIcons name="leaderboard" size={28} color="#bbcbbb" />
          <Text style={[styles.navText, { color: '#bbcbbb' }]}>Leaderboard</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.navItem}>
          <MaterialIcons name="person" size={28} color="#006d37" />
          <Text style={[styles.navText, { color: '#006d37' }]}>Profile</Text>
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
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: '#f7f9ff',
    borderBottomWidth: 4,
    borderBottomColor: '#d1e4fb',
    paddingTop: 40,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#091d2e',
  },
  content: {
    flex: 1,
    padding: 24,
  },
  profileCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#e3efff',
    marginBottom: 32,
    borderBottomWidth: 6, // chunky shadow
  },
  avatarPlaceholder: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#006d37',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  emailText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#091d2e',
  },
  actionContainer: {
    marginTop: 'auto',
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fee2e2',
    paddingVertical: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#f87171',
    gap: 8,
    borderBottomWidth: 6,
  },
  logoutText: {
    color: '#b91c1c',
    fontSize: 18,
    fontWeight: 'bold',
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
