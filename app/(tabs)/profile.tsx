import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Alert } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import ChunkyButton from '../components/ChunkyButton';

export default function Profile() {
  const router = useRouter();
  const { subject } = useLocalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  const user = auth().currentUser;
  
  const [userData, setUserData] = useState<{ username?: string, grade?: string }>({});

  useEffect(() => {
    if (user?.uid) {
      const subscriber = firestore()
        .collection('users')
        .doc(user.uid)
        .onSnapshot(documentSnapshot => {
          if (documentSnapshot && documentSnapshot.exists) {
            setUserData(documentSnapshot.data() as any);
          }
        }, (error) => {
          console.log("Profile listener detached due to logout or error:", error);
        });
      return () => subscriber();
    }
  }, [user]);

  const handleLogout = async () => {
    try {
      await auth().signOut();
      // The _layout.tsx will automatically redirect the user to '/'
    } catch (error: any) {
      Alert.alert("Logout Error", error.message);
    }
  };

  const handleChangePassword = async () => {
    if (user?.email) {
      try {
        await auth().sendPasswordResetEmail(user.email);
        Alert.alert("Email Sent", "A password reset link has been sent to your email address.");
      } catch (error: any) {
        Alert.alert("Error", error.message);
      }
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
            <Text style={styles.avatarText}>
              {userData.username?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'}
            </Text>
          </View>
          <Text style={styles.nameText}>{userData.username || 'Student'}</Text>
          <Text style={styles.emailText}>{user?.email}</Text>
          
          {userData.grade && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>Class {userData.grade}</Text>
            </View>
          )}
        </View>

        <View style={styles.menuContainer}>
          <TouchableOpacity style={styles.menuItem} activeOpacity={0.7} onPress={handleChangePassword}>
            <View style={styles.menuItemLeft}>
              <MaterialIcons name="lock-reset" size={24} color="#006d37" />
              <Text style={styles.menuItemText}>Change Password</Text>
            </View>
            <MaterialIcons name="chevron-right" size={24} color="#bbcbbb" />
          </TouchableOpacity>
        </View>

        <View style={styles.actionContainer}>
          <TouchableOpacity style={styles.logoutButton} activeOpacity={0.7} onPress={handleLogout}>
            <MaterialIcons name="logout" size={24} color="#b91c1c" />
            <Text style={styles.logoutText}>Log Out</Text>
          </TouchableOpacity>
        </View>
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
    marginBottom: 24,
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
  nameText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#091d2e',
    marginBottom: 4,
  },
  emailText: {
    fontSize: 14,
    color: '#6c7b6d',
    marginBottom: 12,
  },
  badge: {
    backgroundColor: '#e3efff',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#d1e4fb',
  },
  badgeText: {
    color: '#004970',
    fontWeight: 'bold',
    fontSize: 14,
  },
  menuContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#e3efff',
    overflow: 'hidden',
    borderBottomWidth: 6, // chunky shadow
    marginBottom: 24,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#ffffff',
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  menuItemText: {
    fontSize: 16,
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
});
