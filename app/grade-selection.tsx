import { View, Text, StyleSheet, Pressable, Alert } from 'react-native';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';

export default function GradeSelection() {
  const router = useRouter();

  const selectGrade = async (grade: number) => {
    try {
      const user = auth().currentUser;
      if (user) {
        await firestore().collection('users').doc(user.uid).update({
          grade,
        });
        router.replace('/subject-selection');
      }
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>SabakTutor</Text>
      <Text style={styles.title}>Select Your Grade</Text>
      <Text style={styles.subtitle}>Choose your class to get started</Text>

      <View style={styles.grid}>
        <Pressable style={styles.card} onPress={() => selectGrade(9)}>
          <Text style={styles.cardIcon}>📘</Text>
          <Text style={styles.cardTitle}>Class 9</Text>
        </Pressable>
        <Pressable style={[styles.card, { opacity: 0.5 }]} disabled={true}>
          <Text style={styles.cardIcon}>📗</Text>
          <Text style={styles.cardTitle}>Class 10</Text>
        </Pressable>
      </View>
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
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#3d4a3e',
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
  cardIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#091d2e',
  },
});
