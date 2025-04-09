import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore';
import { getAuth } from 'firebase/auth';
import Constants from 'expo-constants'; // Import Constants

// Access the configuration variables from Constants
const firebaseConfig = {
  apiKey: Constants.expoConfig?.extra?.firebaseApiKey,
  authDomain: Constants.expoConfig?.extra?.firebaseAuthDomain,
  projectId: Constants.expoConfig?.extra?.firebaseProjectId,
  storageBucket: Constants.expoConfig?.extra?.firebaseStorageBucket,
  messagingSenderId: Constants.expoConfig?.extra?.firebaseMessagingSenderId,
  appId: Constants.expoConfig?.extra?.firebaseAppId,
  measurementId: Constants.expoConfig?.extra?.firebaseMeasurementId,
};

// --- Type checking / Validation (Optional but Recommended) ---
if (
    !firebaseConfig.apiKey ||
    !firebaseConfig.authDomain ||
    !firebaseConfig.projectId ||
    !firebaseConfig.storageBucket ||
    !firebaseConfig.messagingSenderId ||
    !firebaseConfig.appId
) {
   console.error("Firebase configuration is missing! Check your .env file and app.config.js setup.");
   // You might want to throw an error or handle this case more gracefully
   // depending on your app's needs, especially in production builds.
}

// Initialize Firebase
// Note: Added type assertion as validation above might not satisfy TS fully.
const app = initializeApp(firebaseConfig as any);

// Initialize Firestore
export const db = getFirestore(app);

// Initialize Auth
export const auth = getAuth(app);

// Enable Offline Persistence
enableIndexedDbPersistence(db)
  .then(() => console.log("Firestore offline persistence enabled."))
  .catch((err) => {
     console.error("Firestore persistence error: ", err);
     // Handle specific error codes if needed
   });

export default app; 