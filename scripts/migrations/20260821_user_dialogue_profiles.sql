CREATE TABLE IF NOT EXISTS user_dialogue_profiles (
    user_id INT PRIMARY KEY,
    hylik_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333333,
    psychik_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333333,
    pneumatyk_weight DECIMAL(8,6) NOT NULL DEFAULT 0.333334,
    dominant_profile VARCHAR(16) NOT NULL DEFAULT 'neutral',
    confidence DECIMAL(8,6) NOT NULL DEFAULT 0.000000,
    sample_count INT NOT NULL DEFAULT 0,
    profiling_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_conversation_id VARCHAR(128) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_dialogue_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_profile_observations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    conversation_id VARCHAR(128) NULL,
    sample_number INT NOT NULL,
    hylik_evidence DECIMAL(8,6) NOT NULL,
    psychik_evidence DECIMAL(8,6) NOT NULL,
    pneumatyk_evidence DECIMAL(8,6) NOT NULL,
    evidence_strength DECIMAL(8,6) NOT NULL,
    resulting_dominant_profile VARCHAR(16) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_profile_observation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX ix_profile_observation_user (user_id),
    INDEX ix_profile_observation_conversation (conversation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

