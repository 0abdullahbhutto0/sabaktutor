import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons, MaterialIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import Animated, { useSharedValue, useAnimatedStyle, withRepeat, withTiming, withSequence } from 'react-native-reanimated';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import ChunkyButton from './ChunkyButton';

let cachedMasteryPoints: number = 0;
let cachedStreak: number = 0;

export default function TopHeader({ subjectStr }: { subjectStr: string }) {
  const router = useRouter();
  
  const [masteryPoints, setMasteryPoints] = useState<number>(cachedMasteryPoints);
  const [streak, setStreak] = useState<number>(cachedStreak);

  const fireScale = useSharedValue(1);
  const fireOpacity = useSharedValue(0.8);

  useEffect(() => {
    if (streak > 0) {
      fireScale.value = withRepeat(
        withSequence(
          withTiming(1.25, { duration: 300 }),
          withTiming(1, { duration: 300 }),
          withTiming(1, { duration: 1400 }),
        ),
        -1,
        false,
      );
      fireOpacity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 300 }),
          withTiming(0.7, { duration: 300 }),
          withTiming(0.7, { duration: 1400 }),
        ),
        -1,
        false,
      );
    } else {
      fireScale.value = 1;
      fireOpacity.value = 1;
    }
  }, [streak]);

  const animatedFireStyle = useAnimatedStyle(() => ({
    transform: [{ scale: fireScale.value }],
    opacity: fireOpacity.value,
  }));

  useEffect(() => {
    const user = auth().currentUser;
    if (!user) return;

    const unsubscribeUser = firestore()
      .collection("users")
      .doc(user.uid)
      .onSnapshot(
        (doc) => {
          if (doc && doc.data) {
            const data = doc.data();
            if (data) {
              cachedMasteryPoints = data.energyPoints || 0;
              setMasteryPoints(cachedMasteryPoints);

              // Calculate streak
              const dates: string[] = data.activeDates || [];
              if (dates.length > 0) {
                const sorted = [...new Set(dates)].sort((a, b) =>
                  b.localeCompare(a),
                );
                const todayStr = new Date().toISOString().split("T")[0];
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);
                const yesterdayStr = yesterday.toISOString().split("T")[0];

                if (sorted[0] !== todayStr && sorted[0] !== yesterdayStr) {
                  setStreak(0);
                } else {
                  let currentStreak = 0;
                  let checkDate = new Date(sorted[0]);
                  for (let i = 0; i < sorted.length; i++) {
                    if (sorted[i] === checkDate.toISOString().split("T")[0]) {
                      currentStreak++;
                      checkDate.setDate(checkDate.getDate() - 1);
                    } else {
                      break;
                    }
                  }
                  cachedStreak = currentStreak;
                  setStreak(currentStreak);
                }
              } else {
                cachedStreak = 0;
                setStreak(0);
              }
            }
          }
        },
        (error) => {
          console.log("Header User listener error:", error);
        },
      );

    return () => unsubscribeUser();
  }, []);

  return (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        <ChunkyButton
          onPress={() => router.replace("/subject-selection")}
          color="#bfdbfe"
          shadowColor="#60a5fa"
          chunky
          style={{
            paddingVertical: 8,
            paddingHorizontal: 16,
            borderRadius: 24,
          }}
          textStyle={{ color: "#1e3a8a", fontSize: 16, marginLeft: 0 }}
        >
          <MaterialCommunityIcons
            name="menu-down"
            size={24}
            color="#1e3a8a"
          />
          <Text style={{ color: "#1e3a8a", fontSize: 16, fontWeight: "bold" }}>
            {subjectStr === "physics" ? "Physics" : subjectStr === "maths" ? "Maths" : "Comp Sci"}
          </Text>
        </ChunkyButton>
      </View>
      <View style={[styles.headerRight, { gap: 8 }]}>
        <ChunkyButton
          onPress={() => router.push(`/streak?subject=${subjectStr}` as any)}
          color="#fed7aa"
          shadowColor="#f97316"
          chunky
          style={{
            paddingVertical: 8,
            paddingHorizontal: 16,
            borderRadius: 24,
          }}
        >
          <Animated.View style={animatedFireStyle}>
            <MaterialCommunityIcons name="fire" size={28} color="#ea580c" />
          </Animated.View>
          <Text
            style={[
              styles.energyText,
              { color: "#9a3412", marginLeft: 4, fontSize: 18 },
            ]}
          >
            {streak}
          </Text>
        </ChunkyButton>

        <ChunkyButton
          onPress={() => router.navigate(`/(tabs)/leaderboard?subject=${subjectStr}` as any)}
          color="#fed023"
          shadowColor="#d4a300"
          chunky
          style={{
            paddingVertical: 8,
            paddingHorizontal: 16,
            borderRadius: 24,
          }}
        >
          <MaterialIcons name="bolt" size={28} color="#6f5900" />
          <Text style={[styles.energyText, { marginLeft: 2, fontSize: 18 }]}>
            {masteryPoints}
          </Text>
        </ChunkyButton>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: "#f7f9ff",
    borderBottomWidth: 4,
    borderBottomColor: "#d1e4fb",
    paddingTop: 40, // For Android status bar
  },
  headerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
  },
  energyText: {
    color: "#6f5900",
    fontWeight: "bold",
    fontSize: 14,
  },
});
