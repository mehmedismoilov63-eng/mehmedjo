"""
Voice Profiler Module
Handles user identification through voice biometrics
"""

import os
import json
import logging
import threading
import time
import pickle
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    import librosa
    import numpy as np
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score
    VOICE_PROFILING_AVAILABLE = True
except ImportError:
    librosa = None
    np = None
    GaussianMixture = None
    StandardScaler = None
    accuracy_score = None
    VOICE_PROFILING_AVAILABLE = False
    logging.warning("scikit-learn or librosa not installed. Voice profiling disabled.")

from config import Config

logger = logging.getLogger(__name__)

class VoiceProfiler:
    """Voice biometric identification system"""
    
    def __init__(self, config: Config):
        self.config = config
        self.profiles_dir = Path(config.get_voice_profiles_dir())
        self.profiles_dir.mkdir(exist_ok=True)
        
        # Voice processing parameters
        self.sample_rate = 16000
        self.n_mfcc = 13
        self.n_components = 8  # GMM components
        
        # Loaded models
        self.models = {}
        self.scalers = {}
        self.profile_data = {}
        
        # Load existing profiles
        self.load_profiles()
        
    def is_available(self) -> bool:
        """Check if voice profiling is available"""
        return all(lib is not None for lib in [librosa, np, GaussianMixture, StandardScaler])
        
    def extract_features(self, audio_data) -> Optional[Any]:
        """Extract MFCC features from audio data"""
        if not self.is_available():
            return None
            
        try:
            # Convert to float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
                
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(
                y=audio_data,
                sr=self.sample_rate,
                n_mfcc=self.n_mfcc
            )
            
            # Add delta and delta-delta features
            delta_mfccs = librosa.feature.delta(mfccs)
            delta2_mfccs = librosa.feature.delta(mfccs, order=2)
            
            # Concatenate features
            features = np.concatenate([mfccs, delta_mfccs, delta2_mfccs])
            
            # Calculate statistics
            mean_features = np.mean(features, axis=1)
            std_features = np.std(features, axis=1)
            
            # Combine mean and std
            final_features = np.concatenate([mean_features, std_features])
            
            return final_features
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
            
    def register_user(self, name: str, language: str = "uz", telegram_id: str = None) -> bool:
        """Register a new user voice profile"""
        if not self.is_available():
            logger.error("Voice profiling not available")
            return False
            
        try:
            # Check if user already exists
            if name in self.profile_data:
                logger.warning(f"User {name} already exists")
                return False
                
            # Collect voice samples
            logger.info(f"Starting voice registration for {name}")
            
            # This would normally involve collecting multiple samples
            # For now, we'll create a placeholder
            profile = {
                "name": name,
                "language": language,
                "telegram_id": telegram_id,
                "created_at": time.time(),
                "samples_count": 0,
                "model_file": f"{name.lower()}_model.pkl",
                "scaler_file": f"{name.lower()}_scaler.pkl"
            }
            
            # Save profile data
            self.profile_data[name] = profile
            self.save_profiles()
            
            logger.info(f"Voice profile created for {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
            
    def add_voice_sample(self, name: str, audio_data) -> bool:
        """Add voice sample to user profile"""
        if not self.is_available():
            return False
            
        try:
            if name not in self.profile_data:
                logger.error(f"User {name} not found")
                return False
                
            # Extract features
            features = self.extract_features(audio_data)
            if features is None:
                return False
                
            # Load existing samples or create new
            samples_file = self.profiles_dir / f"{name.lower()}_samples.pkl"
            
            if samples_file.exists():
                with open(samples_file, 'rb') as f:
                    samples = pickle.load(f)
            else:
                samples = []
                
            # Add new sample
            samples.append(features)
            
            # Save samples
            with open(samples_file, 'wb') as f:
                pickle.dump(samples, f)
                
            # Update profile
            self.profile_data[name]["samples_count"] = len(samples)
            self.save_profiles()
            
            logger.info(f"Added voice sample for {name} (total: {len(samples)})")
            
            # Train model if we have enough samples
            if len(samples) >= 3:
                self.train_model(name)
                
            return True
            
        except Exception as e:
            logger.error(f"Error adding voice sample: {e}")
            return False
            
    def train_model(self, name: str) -> bool:
        """Train GMM model for user"""
        if not self.is_available():
            return False
            
        try:
            # Load samples
            samples_file = self.profiles_dir / f"{name.lower()}_samples.pkl"
            if not samples_file.exists():
                logger.error(f"No samples found for {name}")
                return False
                
            with open(samples_file, 'rb') as f:
                samples = pickle.load(f)
                
            if len(samples) < 3:
                logger.error(f"Not enough samples for {name}: {len(samples)}")
                return False
                
            # Convert to numpy array
            X = np.array(samples)
            
            # Scale features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Train GMM
            model = GaussianMixture(
                n_components=self.n_components,
                covariance_type='full',
                random_state=42
            )
            model.fit(X_scaled)
            
            # Save model and scaler
            model_file = self.profiles_dir / f"{name.lower()}_model.pkl"
            scaler_file = self.profiles_dir / f"{name.lower()}_scaler.pkl"
            
            with open(model_file, 'wb') as f:
                pickle.dump(model, f)
                
            with open(scaler_file, 'wb') as f:
                pickle.dump(scaler, f)
                
            # Cache in memory
            self.models[name] = model
            self.scalers[name] = scaler
            
            logger.info(f"Trained voice model for {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error training model for {name}: {e}")
            return False
            
    def identify_user(self, audio_data, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """Identify user from voice sample"""
        if not self.is_available():
            return None
            
        try:
            # Extract features
            features = self.extract_features(audio_data)
            if features is None:
                return None
                
            best_match = None
            best_score = 0.0
            
            # Compare against all trained models
            for name, model in self.models.items():
                scaler = self.scalers[name]
                
                # Scale features
                features_scaled = scaler.transform([features])
                
                # Get log likelihood score
                score = model.score(features_scaled)
                
                # Convert to probability-like score
                prob_score = 1.0 / (1.0 + np.exp(-score))
                
                if prob_score > best_score and prob_score >= threshold:
                    best_score = prob_score
                    best_match = name
                    
            if best_match:
                profile = self.profile_data[best_match].copy()
                profile["confidence"] = best_score
                logger.info(f"Identified user: {best_match} (confidence: {best_score:.2f})")
                return profile
            else:
                logger.info("Unknown user detected")
                return None
                
        except Exception as e:
            logger.error(f"Error identifying user: {e}")
            return None
            
    def load_profiles(self):
        """Load existing voice profiles"""
        try:
            profiles_file = self.profiles_dir / "profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    self.profile_data = json.load(f)
                    
                # Load models and scalers
                for name in self.profile_data.keys():
                    model_file = self.profiles_dir / f"{name.lower()}_model.pkl"
                    scaler_file = self.profiles_dir / f"{name.lower()}_scaler.pkl"
                    
                    if model_file.exists() and scaler_file.exists():
                        with open(model_file, 'rb') as f:
                            self.models[name] = pickle.load(f)
                        with open(scaler_file, 'rb') as f:
                            self.scalers[name] = pickle.load(f)
                            
                logger.info(f"Loaded {len(self.profile_data)} voice profiles")
            else:
                logger.info("No existing voice profiles found")
                
        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            
    def save_profiles(self):
        """Save voice profiles to file"""
        try:
            profiles_file = self.profiles_dir / "profiles.json"
            with open(profiles_file, 'w', encoding='utf-8') as f:
                json.dump(self.profile_data, f, indent=2, ensure_ascii=False)
                
            logger.info("Voice profiles saved")
            
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")
            
    def delete_user(self, name: str) -> bool:
        """Delete user profile"""
        try:
            if name not in self.profile_data:
                logger.error(f"User {name} not found")
                return False
                
            # Remove profile data
            del self.profile_data[name]
            
            # Remove cached models
            if name in self.models:
                del self.models[name]
            if name in self.scalers:
                del self.scalers[name]
                
            # Remove files
            files_to_remove = [
                f"{name.lower()}_model.pkl",
                f"{name.lower()}_scaler.pkl",
                f"{name.lower()}_samples.pkl"
            ]
            
            for filename in files_to_remove:
                file_path = self.profiles_dir / filename
                if file_path.exists():
                    file_path.unlink()
                    
            # Save updated profiles
            self.save_profiles()
            
            logger.info(f"Deleted voice profile for {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user {name}: {e}")
            return False
            
    def get_users(self) -> List[Dict[str, Any]]:
        """Get list of all registered users"""
        return list(self.profile_data.values())
        
    def get_user_count(self) -> int:
        """Get number of registered users"""
        return len(self.profile_data)
