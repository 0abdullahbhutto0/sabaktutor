import { View, Text, StyleSheet, ScrollView, Pressable } from 'react-native';
import { useState, useEffect } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';
import ChunkyButton from './components/ChunkyButton';

export default function SubjectSelection() {
  const { subject } = useLocalSearchParams();
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [selectedSubject, setSelectedSubject] = useState<string | null>(typeof subject === 'string' ? subject : 'physics');

  useEffect(() => {
    const fetchUser = async () => {
      const currentUser = auth().currentUser;
      if (currentUser) {
        const userDoc = await firestore().collection('users').doc(currentUser.uid).get();
        if (userDoc.data()) {
          const data = userDoc.data();
          if (data?.username) {
            setUsername(data.username);
          }
        }
      }
    };
    fetchUser();
  }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.headerTitle}>SELECT YOUR SUBJECTS (SINDH TEXTBOOK BOARD)</Text>
      
      <View style={styles.list}>
        {/* Maths - Disabled for now */}
        <Pressable 
          disabled={true}
          style={[
            styles.subjectCard, 
            { opacity: 0.5 }
          ]}
        >
          <View style={[styles.iconContainer, { backgroundColor: '#bbcbbb' }]}>
            <MaterialCommunityIcons name="sigma" size={28} color="#091d2e" />
          </View>
          <View style={styles.textContainer}>
            <Text style={styles.subjectTitle}>Maths</Text>
            <Text style={styles.subjectSubtitle}>Logic & Problem Solving (Coming Soon)</Text>
          </View>
          <MaterialIcons 
            name="radio-button-unchecked" 
            size={24} 
            color="#bbcbbb" 
          />
        </Pressable>

        {/* Physics */}
        <Pressable 
          style={({ pressed }) => [
            styles.subjectCard, 
            selectedSubject === 'physics' && styles.subjectCardSelected,
            pressed && styles.cardPressed
          ]}
          onPress={() => setSelectedSubject('physics')}
        >
          <View style={[styles.iconContainer, { backgroundColor: '#4ade80' }]}>
            <MaterialCommunityIcons name="flask" size={28} color="#091d2e" />
          </View>
          <View style={styles.textContainer}>
            <Text style={styles.subjectTitle}>Physics</Text>
            <Text style={styles.subjectSubtitle}>Laws of Motion & Energy</Text>
          </View>
          <MaterialIcons 
            name={selectedSubject === 'physics' ? "radio-button-checked" : "radio-button-unchecked"} 
            size={24} 
            color={selectedSubject === 'physics' ? "#006d37" : "#d1e4fb"} 
          />
        </Pressable>

        {/* Computer Science */}
        <Pressable 
          style={({ pressed }) => [
            styles.subjectCard, 
            selectedSubject === 'computer' && styles.subjectCardSelected,
            pressed && styles.cardPressed
          ]}
          onPress={() => setSelectedSubject('computer')}
        >
          <View style={[styles.iconContainer, { backgroundColor: '#60a5fa' }]}>
            <MaterialIcons name="laptop-mac" size={28} color="#091d2e" />
          </View>
          <View style={styles.textContainer}>
            <Text style={styles.subjectTitle}>Computer Science</Text>
            <Text style={styles.subjectSubtitle}>Coding & Systems</Text>
          </View>
          <MaterialIcons 
            name={selectedSubject === 'computer' ? "radio-button-checked" : "radio-button-unchecked"} 
            size={24} 
            color={selectedSubject === 'computer' ? "#006d37" : "#d1e4fb"} 
          />
        </Pressable>
      </View>

      <ChunkyButton 
        title="Ready to Learn! ➔" 
        onPress={() => router.push(`/quiz-selection?subject=${selectedSubject}`)}
        style={styles.button}
      />
      
      <Text style={styles.footerText}>
        By continuing, you agree to our privacy guidelines. SabakTutor keeps your learning journey anonymous and safe.
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
  },
  contentContainer: {
    padding: 24,
    paddingTop: 60,
  },
  headerTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#006d37',
    marginBottom: 16,
  },
  list: {
    gap: 16,
    marginBottom: 32,
  },
  subjectCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 16,
    borderWidth: 2,
    borderColor: '#e3efff',
  },
  subjectCardSelected: {
    borderColor: '#006d37',
    borderBottomWidth: 4,
  },
  cardPressed: {
    marginTop: 2,
    marginBottom: -2,
    opacity: 0.9,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  textContainer: {
    flex: 1,
  },
  subjectTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 4,
  },
  subjectSubtitle: {
    fontSize: 12,
    color: '#3d4a3e',
  },
  button: {
    marginBottom: 16,
  },
  footerText: {
    fontSize: 10,
    color: '#6c7b6d',
    textAlign: 'center',
    paddingHorizontal: 16,
  },
});
