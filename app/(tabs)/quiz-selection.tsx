import { MaterialCommunityIcons, MaterialIcons } from "@expo/vector-icons";
import auth from "@react-native-firebase/auth";
import firestore from "@react-native-firebase/firestore";
import { useLocalSearchParams, useRouter, useGlobalSearchParams } from "expo-router";
import React, { useEffect, useRef } from "react";
import {
  Dimensions,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  Modal,
} from "react-native";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle, Defs, Path, Pattern, Rect } from "react-native-svg";
import ChunkyButton from "../components/ChunkyButton";
import TopHeader from "../components/TopHeader";
import {
  BOOK_CHAPTERS,
  CHAPTER_TITLES,
  preloadNextQuizzes,
} from "../services/quizService";

const { width } = Dimensions.get("window");
const MAP_WIDTH = Math.min(width - 48, 400); // Responsive max width
const CENTER_X = MAP_WIDTH / 2;
const RIGHT_X = MAP_WIDTH - 60;
const LEFT_X = 60;
const NODE_SIZE = 96;

// Pulsing halo component for the current level node
const CurrentNodeHalo = () => {
  const ring1Scale = useSharedValue(1);
  const ring1Opacity = useSharedValue(0.8);
  const ring2Scale = useSharedValue(1);
  const ring2Opacity = useSharedValue(0.6);

  React.useEffect(() => {
    // Ring 1: continuous pulse outward
    ring1Scale.value = withRepeat(
      withTiming(1.8, { duration: 2000, easing: Easing.out(Easing.ease) }),
      -1,
      false,
    );
    ring1Opacity.value = withRepeat(
      withTiming(0, { duration: 2000, easing: Easing.out(Easing.ease) }),
      -1,
      false,
    );
    // Ring 2: same but staggered by 1s
    ring2Scale.value = withDelay(
      1000,
      withRepeat(
        withTiming(1.8, { duration: 2000, easing: Easing.out(Easing.ease) }),
        -1,
        false,
      ),
    );
    ring2Opacity.value = withDelay(
      1000,
      withRepeat(
        withTiming(0, { duration: 2000, easing: Easing.out(Easing.ease) }),
        -1,
        false,
      ),
    );
  }, []);

  const ring1Style = useAnimatedStyle(() => ({
    transform: [{ scale: ring1Scale.value }],
    opacity: ring1Opacity.value,
  }));
  const ring2Style = useAnimatedStyle(() => ({
    transform: [{ scale: ring2Scale.value }],
    opacity: ring2Opacity.value,
  }));

  const baseRing: any = {
    position: "absolute",
    width: NODE_SIZE + 16,
    height: NODE_SIZE + 16,
    borderRadius: (NODE_SIZE + 16) / 2,
    borderWidth: 4,
    borderColor: "#3b82f6",
  };

  return (
    <>
      <Animated.View style={[baseRing, ring1Style]} />
      <Animated.View style={[baseRing, ring2Style]} />
    </>
  );
};

let cachedProgress: Record<string, boolean> = {};
let cachedMasteryPoints: number = 0;
let cachedStreak: number = 0;
let hasPreloadedSubjects: Record<string, boolean> = {};
let currentUserCacheId: string = "";

export default function MasteryMap() {
  const router = useRouter();
  const { subject, completedChapter } = useGlobalSearchParams<{ subject?: string; completedChapter?: string }>();
  const subjectStr = subject || "physics";
  const bookId = subjectStr === "physics" ? "phy_9" : "cs_9";

  const scrollViewRef = useRef<ScrollView>(null);

  const [progress, setProgress] =
    React.useState<Record<string, boolean>>(cachedProgress);
  const [masteryPoints, setMasteryPoints] =
    React.useState<number>(cachedMasteryPoints);
  const [streak, setStreak] = React.useState<number>(cachedStreak);
  const [userId, setUserId] = React.useState<string | null>(null);
  
  const [showCompletionModal, setShowCompletionModal] = React.useState(false);

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
    setUserId(user.uid);

    if (user.uid !== currentUserCacheId) {
      cachedProgress = {};
      cachedMasteryPoints = 0;
      cachedStreak = 0;
      hasPreloadedSubjects = {};
      currentUserCacheId = user.uid;
      setProgress({});
      setMasteryPoints(0);
      setStreak(0);
    }

    if (!hasPreloadedSubjects[subjectStr]) {
      preloadNextQuizzes(0, subjectStr);
      hasPreloadedSubjects[subjectStr] = true;
    }

    // Listen to user progress
    const unsubscribeProgress = firestore()
      .collection("users")
      .doc(user.uid)
      .collection("progress")
      .onSnapshot(
        (snapshot) => {
          const newProgress: Record<string, boolean> = {};
          if (snapshot && snapshot.forEach) {
            snapshot.forEach((doc) => {
              if (doc && doc.data && doc.data().passed) {
                newProgress[doc.id] = true;
              }
            });
          }
          cachedProgress = newProgress;
          setProgress(newProgress);
        },
        (error) => {
          console.log("Progress listener error:", error);
        },
      );

    // Listen to user doc for energyPoints and activeDates
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
          console.log("User listener error:", error);
        },
      );

    return () => {
      unsubscribeProgress();
      unsubscribeUser();
    };
  }, [subjectStr]);

  const chaptersMap = BOOK_CHAPTERS[subjectStr] || BOOK_CHAPTERS["physics"];
  const titlesMap = CHAPTER_TITLES[subjectStr] || CHAPTER_TITLES["physics"];
  const chaptersCount = Object.keys(chaptersMap).length;

  const nodes = Array.from({ length: chaptersCount * 2 }).map((_, i) => {
    const chapterNum = Math.floor(i / 2) + 1;
    const level = `ch${chapterNum}`;
    const type = i % 2 === 0 ? "lesson" : "quiz";
    const route = type;
    const chapterName = titlesMap[level] || `Chapter ${chapterNum}`;
    const typeLabel = type === "lesson" ? "Lesson" : "Quest";
    const globalId = userId ? `${type}_${userId}_${bookId}_${level}` : "";
    return {
      index: i,
      type,
      route,
      level,
      title: chapterName,
      typeLabel,
      globalId,
    };
  });

  const isCompleted = (globalId: string) => !!progress[globalId];

  const isUnlocked = (index: number) => {
    if (index === 0) return true;
    if (isCompleted(nodes[index].globalId)) return true;
    const prevNode = nodes[index - 1];
    return isCompleted(prevNode.globalId);
  };

  const hasUnattemptedMocks = React.useMemo(() => {
    for (let i = 1; i <= chaptersCount; i++) {
      const level = `ch${i}`;
      const lessonCompleted = progress[`lesson_${userId}_${bookId}_${level}`];
      const quizCompleted = progress[`quiz_${userId}_${bookId}_${level}`];
      const mockCompleted = progress[`descriptive_${userId}_${bookId}_${level}`];
      if (lessonCompleted && quizCompleted && !mockCompleted) {
        return true;
      }
    }
    return false;
  }, [progress, chaptersCount, userId, bookId]);

  useEffect(() => {
    if (completedChapter) {
      const level = completedChapter;
      const lessonCompleted = progress[`lesson_${userId}_${bookId}_${level}`];
      const quizCompleted = progress[`quiz_${userId}_${bookId}_${level}`];
      const mockCompleted = progress[`descriptive_${userId}_${bookId}_${level}`];
      
      if (lessonCompleted && quizCompleted && !mockCompleted) {
        setShowCompletionModal(true);
        // Clear param to prevent showing again on subsequent remounts
        router.setParams({ completedChapter: undefined });
      }
    }
  }, [completedChapter, progress, userId, bookId]);

  useEffect(() => {
    const highestUnlockedIndex = nodes.reduce((highest, _node, i) => {
      return isUnlocked(i) ? i : highest;
    }, 0);
    const { height: screenHeight } = Dimensions.get("window");
    const targetY = Math.max(
      0,
      highestUnlockedIndex * 140 - screenHeight / 2 + 140,
    );
    // Scroll instantly on first paint, animated on progress updates
    scrollViewRef.current?.scrollTo({ y: targetY, animated: false });
  }, [progress, subjectStr]);

  // Compute the "current level" = highest unlocked node that is NOT completed
  const currentLevelIndex = React.useMemo(() => {
    let current = 0;
    for (let i = 0; i < nodes.length; i++) {
      if (isUnlocked(i) && !isCompleted(nodes[i].globalId)) {
        current = i;
        break;
      }
      if (isUnlocked(i)) current = i;
    }
    return current;
  }, [progress, subjectStr, userId]);

  const getXForIndex = (index: number) => {
    const mod = index % 4;
    if (mod === 0) return CENTER_X;
    if (mod === 1) return RIGHT_X;
    if (mod === 2) return CENTER_X;
    return LEFT_X;
  };

  const getIconName = (type: string, completed: boolean) => {
    if (completed) return "check-circle";
    if (type === "lesson") return "menu-book";
    if (type === "descriptive") return "edit-document";
    return "star";
  };

  const renderPath = (i: number) => {
    if (i >= nodes.length - 1) return null;
    const startX = getXForIndex(i);
    const endX = getXForIndex(i + 1);
    const startY = i * 140;
    const endY = (i + 1) * 140;
    const midY = startY + 70;

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

  const totalHeight = Math.max((nodes.length - 1) * 140 + NODE_SIZE + 80, 600);

  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Top App Bar */}
      <TopHeader subjectStr={subjectStr} />

      <ScrollView
        ref={scrollViewRef}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Dotted canvas background */}
        <View
          style={{
            width: MAP_WIDTH,
            height: totalHeight,
            alignSelf: "center",
            position: "relative",
          }}
        >
          <Svg
            width={MAP_WIDTH}
            height={totalHeight}
            style={{ position: "absolute", top: 0, left: 0 }}
            pointerEvents="none"
          >
            <Defs>
              <Pattern
                id="dotPattern"
                x="0"
                y="0"
                width="24"
                height="24"
                patternUnits="userSpaceOnUse"
              >
                <Circle
                  cx="1.5"
                  cy="1.5"
                  r="1.5"
                  fill="#cbd5e1"
                  opacity="0.35"
                />
              </Pattern>
            </Defs>
            <Rect
              x="0"
              y="0"
              width={MAP_WIDTH}
              height={totalHeight}
              fill="url(#dotPattern)"
            />
          </Svg>

          {/* Dashed Path (SVG) */}
          <Svg
            height={totalHeight}
            width={MAP_WIDTH}
            style={{ position: "absolute", top: NODE_SIZE / 2, left: 0 }}
          >
            {nodes.map((_, i) => renderPath(i))}
          </Svg>

          {nodes.map((node, i) => {
            const x = getXForIndex(i);
            const y = i * 140;
            const completed = isCompleted(node.globalId);
            const unlocked = isUnlocked(i);
            const iconName = getIconName(node.type, completed) as any;

            return (
              <View
                key={`node-${i}`}
                style={[
                  styles.nodeContainer,
                  { left: x - NODE_SIZE / 2, top: y },
                ]}
              >
                {i === currentLevelIndex && (
                  <View
                    style={{
                      position: "absolute",
                      top: 0,
                      alignSelf: "center",
                      width: NODE_SIZE,
                      height: NODE_SIZE,
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <CurrentNodeHalo />
                  </View>
                )}
                <Pressable
                  style={({ pressed }) => [
                    !unlocked
                      ? styles.nodeLocked
                      : completed
                        ? styles.nodeCompleted
                        : styles.nodeUnlocked,
                    unlocked && pressed && styles.nodePressed,
                  ]}
                  onPress={() => {
                    if (unlocked) {
                      router.push(
                        `/${node.route}/${node.level}?subject=${subjectStr}` as any,
                      );
                    }
                  }}
                >
                  {!unlocked ? (
                    <MaterialIcons name="lock" size={40} color="#bbcbbb" />
                  ) : (
                    <MaterialIcons name={iconName} size={48} color="#ffffff" />
                  )}
                </Pressable>
                  <View
                    style={[
                      !unlocked
                        ? styles.nodeLabelLocked
                        : completed
                          ? styles.nodeLabelCompleted
                          : styles.nodeLabelUnlocked,
                    ]}
                  >
                    <View
                      style={[
                        styles.typeBadge,
                        node.type === "lesson"
                          ? styles.typeBadgeLesson
                          : styles.typeBadgeQuest,
                        !unlocked && { opacity: 0.5 },
                      ]}
                    >
                      <MaterialCommunityIcons
                        name={
                          node.type === "lesson"
                            ? "book-open-variant"
                            : "sword-cross"
                        }
                        size={12}
                        color={
                          node.type === "lesson"
                            ? "#1e3a8a"
                            : "#7c2d12"
                        }
                      />
                      <Text
                        style={[
                          styles.typeBadgeText,
                          node.type === "lesson"
                            ? { color: "#1e3a8a" }
                            : { color: "#7c2d12" },
                        ]}
                      >
                        {node.typeLabel}
                      </Text>
                    </View>
                    <Text
                      style={
                        !unlocked
                          ? styles.nodeLabelTextLocked
                          : completed
                            ? styles.nodeLabelTextCompleted
                            : styles.nodeLabelTextUnlocked
                      }
                      numberOfLines={2}
                    >
                      {node.title}
                    </Text>
                  </View>
              </View>
            );
          })}
        </View>
      </ScrollView>

      {/* Floating Action Button for Study Buddy Chat */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push(`/chat?subject=${subjectStr}` as any)}
        activeOpacity={0.8}
      >
        <Image
          source={require("../../assets/images/sleeping.png")}
          style={{ width: 64, height: 64, borderRadius: 32 }}
        />
      </TouchableOpacity>



      <Modal
        visible={showCompletionModal}
        transparent={true}
        animationType="fade"
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContainer}>
            <Image
              source={require("../../assets/images/thinking.png")}
              style={{ width: 80, height: 80, borderRadius: 40, marginBottom: 16 }}
            />
            <Text style={styles.modalTitle}>Chapter Completed! 🎉</Text>
            <Text style={styles.modalBody}>
              You've mastered the concepts! Are you ready to test your deep understanding with a descriptive Mock Exam?
            </Text>
            
            <TouchableOpacity 
              style={styles.modalButtonPrimary}
              onPress={() => {
                setShowCompletionModal(false);
                router.replace({ pathname: "/mock-exams", params: { subject: subjectStr } });
              }}
            >
              <Text style={styles.modalButtonText}>Take Mock Exam</Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.modalButtonSecondary}
              onPress={() => setShowCompletionModal(false)}
            >
              <Text style={[styles.modalButtonText, { color: '#64748B' }]}>Maybe Later</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#f7f9ff",
  },
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
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#006d37",
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
  },
  energyBadge: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fed023",
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
    borderBottomWidth: 4,
    borderBottomColor: "#6f5900",
  },
  energyText: {
    color: "#6f5900",
    fontWeight: "bold",
    fontSize: 14,
  },
  scrollContent: {
    paddingVertical: 48,
    paddingHorizontal: 24,
    gap: 48,
  },
  nodeContainer: {
    position: "absolute",
    alignItems: "center",
    width: NODE_SIZE + 80,
    marginLeft: -40,
  },
  nodeCompleted: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE / 2,
    backgroundColor: "#2ecc71",
    borderWidth: 4,
    borderColor: "#006d37",
    justifyContent: "center",
    alignItems: "center",
    borderBottomWidth: 8,
  },
  nodePressed: {
    borderBottomWidth: 0,
    marginTop: 8,
  },
  nodeLabelCompleted: {
    marginTop: 8,
    width: NODE_SIZE + 60,
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "#d1e4fb",
    alignItems: "center",
  },
  nodeLabelTextCompleted: {
    fontWeight: "bold",
    fontSize: 12,
    color: "#091d2e",
    textAlign: "center",
  },
  nodeUnlocked: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE / 2,
    backgroundColor: "#3B82F6",
    borderWidth: 4,
    borderColor: "#1D4ED8",
    justifyContent: "center",
    alignItems: "center",
    borderBottomWidth: 8,
  },
  nodeLabelUnlocked: {
    marginTop: 8,
    width: NODE_SIZE + 60,
    backgroundColor: "#ffffff",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "#3B82F6",
    alignItems: "center",
  },
  nodeLabelTextUnlocked: {
    fontWeight: "bold",
    fontSize: 12,
    color: "#1D4ED8",
    textAlign: "center",
  },
  nodeLocked: {
    width: NODE_SIZE,
    height: NODE_SIZE,
    borderRadius: NODE_SIZE / 2,
    backgroundColor: "#e3efff",
    borderWidth: 4,
    borderColor: "#bbcbbb",
    justifyContent: "center",
    alignItems: "center",
    opacity: 0.6,
  },
  nodeLabelLocked: {
    marginTop: 8,
    width: NODE_SIZE + 60,
    backgroundColor: "#d9eaff",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "#bbcbbb",
    opacity: 0.6,
    alignItems: "center",
  },
  nodeLabelTextLocked: {
    fontWeight: "bold",
    fontSize: 12,
    color: "#3d4a3e",
    textAlign: "center",
  },
  typeBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    marginBottom: 2,
  },
  typeBadgeLesson: {
    backgroundColor: "#dbeafe",
  },
  typeBadgeQuest: {
    backgroundColor: "#ffedd5",
  },
  typeBadgeChallenge: {
    backgroundColor: "#ede9fe",
  },
  typeBadgeText: {
    fontSize: 10,
    fontWeight: "900",
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  bottomNav: {
    flexDirection: "row",
    backgroundColor: "#ffffff",
    borderTopWidth: 2,
    borderTopColor: "#e3efff",
    paddingBottom: 24,
    paddingTop: 12,
    justifyContent: "space-around",
    alignItems: "center",
  },
  navItem: {
    alignItems: "center",
    position: "relative",
    flex: 1,
  },
  navText: {
    fontSize: 12,
    fontWeight: "bold",
    marginTop: 4,
  },
  comingSoonBadge: {
    position: "absolute",
    top: -8,
    right: 16,
    backgroundColor: "#fed023",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#6f5900",
  },
  comingSoonText: {
    fontSize: 8,
    fontWeight: "900",
    color: "#6f5900",
  },
  notificationDot: {
    position: 'absolute',
    top: -2,
    right: 20,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#ef4444',
    borderWidth: 1,
    borderColor: '#ffffff',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  modalContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    width: '100%',
    maxWidth: 340,
    elevation: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#006d37',
    marginBottom: 12,
    textAlign: 'center',
  },
  modalBody: {
    fontSize: 15,
    color: '#475569',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  modalButtonPrimary: {
    backgroundColor: '#006d37',
    width: '100%',
    paddingVertical: 14,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 12,
  },
  modalButtonSecondary: {
    backgroundColor: '#f1f5f9',
    width: '100%',
    paddingVertical: 14,
    borderRadius: 16,
    alignItems: 'center',
  },
  modalButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  fab: {
    position: "absolute",
    bottom: 24,
    right: 24,
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: "#ffffff",
    justifyContent: "center",
    alignItems: "center",
    elevation: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    borderWidth: 2,
    borderColor: "#60A5FA",
  },
});
