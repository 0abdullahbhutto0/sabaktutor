import { View, Text, StyleSheet, TouchableOpacity, ScrollView } from 'react-native';
import { useState, useEffect } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';
import { MaterialIcons, MaterialCommunityIcons } from '@expo/vector-icons';

export default function SubjectSelection() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [selectedSubject, setSelectedSubject] = useState<string | null>('physics');

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

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <Text style={styles.headerTitle}>SELECT YOUR SUBJECTS (SINDH TEXTBOOK BOARD)</Text>
      
      <View style={styles.list}>
        {/* Maths */}
        <TouchableOpacity 
          activeOpacity={0.7} 
          style={[styles.subjectCard, selectedSubject === 'maths' && styles.subjectCardSelected]}
          onPress={() => setSelectedSubject('maths')}
        >
          <View style={[styles.iconContainer, { backgroundColor: '#fbbf24' }]}>
            <MaterialCommunityIcons name="sigma" size={28} color="#091d2e" />
          </View>
          <View style={styles.textContainer}>
            <Text style={styles.subjectTitle}>Maths</Text>
            <Text style={styles.subjectSubtitle}>Logic & Problem Solving</Text>
          </View>
          <MaterialIcons 
            name={selectedSubject === 'maths' ? "radio-button-checked" : "radio-button-unchecked"} 
            size={24} 
            color={selectedSubject === 'maths' ? "#006d37" : "#d1e4fb"} 
          />
        </TouchableOpacity>

        {/* Physics */}
        <TouchableOpacity 
          activeOpacity={0.7} 
          style={[styles.subjectCard, selectedSubject === 'physics' && styles.subjectCardSelected]}
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
        </TouchableOpacity>

        {/* Computer Science */}
        <TouchableOpacity 
          activeOpacity={0.7} 
          style={[styles.subjectCard, selectedSubject === 'computer' && styles.subjectCardSelected]}
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
        </TouchableOpacity>
      </View>

      <TouchableOpacity 
        activeOpacity={0.7} 
        style={styles.button}
        onPress={() => router.push('/quiz-selection')}
      >
        <Text style={styles.buttonText}>Ready to Learn! ➔</Text>
      </TouchableOpacity>
      
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
    backgroundColor: '#206b38',
    paddingVertical: 16,
    borderRadius: 8,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#104d23',
    marginBottom: 16,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  footerText: {
    fontSize: 10,
    color: '#6c7b6d',
    textAlign: 'center',
    paddingHorizontal: 16,
  },
});
