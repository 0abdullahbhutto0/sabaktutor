import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useState, useEffect } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';

export default function SubjectSelection() {
  const router = useRouter();
  const [username, setUsername] = useState('');

  useEffect(() => {
    const fetchUser = async () => {
      const currentUser = auth().currentUser;
      if (currentUser) {
        const userDoc = await firestore().collection('users').doc(currentUser.uid).get();
        if (userDoc.exists) {
          const data = userDoc.data();
          if (data?.username) {
            setUsername(data.username);
          }
        }
      }
    };
    fetchUser();
  }, []);

  const handleLogout = async () => {
    await auth().signOut();
    router.replace('/');
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>SabakTutor</Text>
      {username ? <Text style={styles.greeting}>Hi {username},</Text> : null}
      <Text style={styles.title}>Choose a Subject</Text>
      
      <View style={styles.grid}>
        <Pressable style={styles.card} onPress={() => router.push('/quiz-selection')}>
          <Text style={styles.cardIcon}>💻</Text>
          <Text style={styles.cardTitle}>Computer Science</Text>
        </Pressable>
        <Pressable style={[styles.card, styles.cardDisabled]} disabled={true}>
          <Text style={styles.cardIcon}>📐</Text>
          <Text style={styles.cardTitle}>Mathematics</Text>
        </Pressable>
        <Pressable style={[styles.card, styles.cardDisabled]} disabled={true}>
          <Text style={styles.cardIcon}>⚛️</Text>
          <Text style={styles.cardTitle}>Physics</Text>
        </Pressable>
        <Pressable style={[styles.card, styles.cardDisabled]} disabled={true}>
          <Text style={styles.cardIcon}>🧪</Text>
          <Text style={styles.cardTitle}>Chemistry</Text>
        </Pressable>
        <Pressable style={[styles.card, styles.cardDisabled]} disabled={true}>
          <Text style={styles.cardIcon}>🧬</Text>
          <Text style={styles.cardTitle}>Biology</Text>
        </Pressable>
      </View>

      <Pressable style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Logout</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    paddingTop: 60,
  },
  header: {
    fontSize: 22,
    fontWeight: '600',
    color: '#006d37',
    marginBottom: 8,
  },
  greeting: {
    fontSize: 20,
    fontWeight: '600',
    color: '#3d4a3e',
    marginBottom: 4,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 32,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    width: '48%',
    backgroundColor: '#ffffff',
    padding: 24,
    borderRadius: 16,
    marginBottom: 16,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#e3efff',
  },
  cardDisabled: {
    opacity: 0.5,
  },
  cardIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#091d2e',
  },
  logoutButton: {
    marginTop: 'auto',
    paddingVertical: 16,
    alignItems: 'center',
  },
  logoutText: {
    color: '#e53935',
    fontSize: 16,
    fontWeight: '600',
  },
});
