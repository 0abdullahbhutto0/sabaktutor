import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, SafeAreaView, TouchableOpacity } from 'react-native';
import { useRouter, useGlobalSearchParams, Stack } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import firestore from '@react-native-firebase/firestore';
import auth from '@react-native-firebase/auth';

interface UserData {
  id: string;
  username: string;
  energyPoints: number;
  rank: number;
}

export default function Leaderboard() {
  const router = useRouter();
  const { subject } = useGlobalSearchParams<{ subject?: string }>();
  const subjectStr = subject || 'physics';
  
  const [users, setUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const currentUserId = auth().currentUser?.uid;

  useEffect(() => {
    let unsubscribeSnapshot: () => void;

    // Wait for auth to be ready, otherwise we get permission-denied
    const unsubscribeAuth = auth().onAuthStateChanged((user) => {
      if (user) {
        unsubscribeSnapshot = firestore()
          .collection('users')
          .orderBy('energyPoints', 'desc')
          .limit(50)
          .onSnapshot((snapshot) => {
            const fetchedUsers: UserData[] = [];
            snapshot.docs.forEach((doc, index) => {
              fetchedUsers.push({
                id: doc.id,
                username: doc.data().username || 'Anonymous',
                energyPoints: doc.data().energyPoints || 0,
                rank: index + 1
              });
            });
            setUsers(fetchedUsers);
            setLoading(false);
          }, (error) => {
            console.error("Error fetching leaderboard:", error);
            setLoading(false);
          });
      } else {
        if (unsubscribeSnapshot) {
          unsubscribeSnapshot();
        }
        setUsers([]);
        setLoading(false);
      }
    });

    return () => {
      unsubscribeAuth();
      if (unsubscribeSnapshot) {
        unsubscribeSnapshot();
      }
    };
  }, []);

  const renderItem = ({ item }: { item: UserData }) => {
    const isCurrentUser = item.id === currentUserId;
    return (
      <View style={[styles.userRow, isCurrentUser && styles.currentUserRow]}>
        <View style={styles.rankContainer}>
          {item.rank === 1 ? <Text style={styles.medal}>🥇</Text> :
           item.rank === 2 ? <Text style={styles.medal}>🥈</Text> :
           item.rank === 3 ? <Text style={styles.medal}>🥉</Text> :
           <Text style={styles.rankText}>{item.rank}</Text>}
        </View>
        <View style={styles.avatarCircle}>
          <Text style={styles.avatarText}>{item.username.charAt(0).toUpperCase()}</Text>
        </View>
        <View style={styles.userInfo}>
          <Text style={[styles.username, isCurrentUser && styles.currentUsername]}>
            {item.username} {isCurrentUser && '(You)'}
          </Text>
        </View>
        <View style={styles.scoreContainer}>
          <MaterialIcons name="bolt" size={20} color="#6f5900" />
          <Text style={styles.scoreText}>{item.energyPoints}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <TouchableOpacity 
          onPress={() => router.navigate({ pathname: '/(tabs)/quiz-selection', params: { subject: subjectStr } })} 
          style={styles.backButton}
        >
          <MaterialIcons name="arrow-back" size={24} color="#006d37" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Leaderboard</Text>
        <View style={{ width: 40 }} />
      </View>
      
      <View style={styles.banner}>
        <Text style={styles.bannerTitle}>Top Scholars</Text>
        <Text style={styles.bannerSub}>Compete by earning energy points!</Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <Text style={styles.loadingText}>Loading ranks...</Text>
        </View>
      ) : (
        <FlatList 
          data={users}
          keyExtractor={item => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
        />
      )}

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
    paddingTop: 40,
  },
  backButton: {
    padding: 8,
    marginLeft: -8,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#006d37',
  },
  banner: {
    backgroundColor: '#156c40',
    paddingVertical: 24,
    paddingHorizontal: 24,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#004970',
  },
  bannerTitle: {
    fontSize: 28,
    fontWeight: '900',
    color: '#ffffff',
    marginBottom: 4,
  },
  bannerSub: {
    fontSize: 14,
    color: '#d1e4fb',
    fontWeight: '600',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: '#6c7b6d',
    fontWeight: '600',
  },
  listContent: {
    padding: 24,
    paddingBottom: 48,
  },
  userRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  currentUserRow: {
    backgroundColor: '#e3efff',
    borderColor: '#3B82F6',
  },
  rankContainer: {
    width: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  medal: {
    fontSize: 24,
  },
  rankText: {
    fontSize: 18,
    fontWeight: '800',
    color: '#6c7b6d',
  },
  avatarCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#bbcbbb',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
    marginRight: 16,
  },
  avatarText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  userInfo: {
    flex: 1,
  },
  username: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#091d2e',
  },
  currentUsername: {
    color: '#1D4ED8',
  },
  scoreContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fed023',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderBottomWidth: 3,
    borderBottomColor: '#6f5900',
  },
  scoreText: {
    fontSize: 16,
    fontWeight: '900',
    color: '#6f5900',
    marginLeft: 4,
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
});
