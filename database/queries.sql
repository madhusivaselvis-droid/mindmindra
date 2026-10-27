 -- 1. Enable UUID Extension                                                                                                                                             
    CREATE EXTENSION IF NOT EXISTS pgcrypto;                                                                                                                                
                                                                                                                                                                            
    -- 2. Alembic Version Tracking                                                                                                                                          
    CREATE TABLE IF NOT EXISTS alembic_version (                                                                                                                            
        version_num VARCHAR(64) NOT NULL PRIMARY KEY                                                                                                                        
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- 3. Users Table                                                                                                                                                       
    CREATE TABLE IF NOT EXISTS users (                                                                                                                                      
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        name VARCHAR(120) NOT NULL,                                                                                                                                         
        email VARCHAR(255) NOT NULL UNIQUE,                                                                                                                                 
        password_hash TEXT NOT NULL,                                                                                                                                        
        role VARCHAR(30) NOT NULL,                                                                                                                                          
        is_active BOOLEAN NOT NULL DEFAULT TRUE,                                                                                                                            
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC')                                                                                           
    );                                                                                                                                                                      
    CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);                                                                                                              
    CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);                                                                                                                
                                                                                                                                                                            
    -- 4. Patients Table                                                                                                                                                    
    CREATE TABLE IF NOT EXISTS patients (                                                                                                                                   
        id VARCHAR(36) PRIMARY KEY REFERENCES users(id),                                                                                                                    
        preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',                                                                                                               
        region VARCHAR(120),                                                                                                                                                
        deleted_at TIMESTAMP WITHOUT TIME ZONE                                                                                                                              
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- 5. Caregiver-Patient Assignments                                                                                                                                     
    CREATE TABLE IF NOT EXISTS caregiver_patient_assignments (                                                                                                              
        caregiver_id VARCHAR(36) NOT NULL REFERENCES users(id),                                                                                                             
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),                                                                                          
        PRIMARY KEY (caregiver_id, patient_id)                                                                                                                              
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- 6. Games Catalog                                                                                                                                                     
    CREATE TABLE IF NOT EXISTS games (                                                                                                                                      
        game_type VARCHAR(50) PRIMARY KEY,                                                                                                                                  
        display_name VARCHAR(120) NOT NULL                                                                                                                                  
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- 7. Game Sessions                                                                                                                                                     
    CREATE TABLE IF NOT EXISTS game_sessions (                                                                                                                              
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        game_type VARCHAR(50) NOT NULL REFERENCES games(game_type),                                                                                                         
        difficulty_level INTEGER NOT NULL,                                                                                                                                  
        started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC'),                                                                                          
        completed_at TIMESTAMP WITHOUT TIME ZONE                                                                                                                            
    );                                                                                                                                                                      
    CREATE INDEX IF NOT EXISTS ix_game_session_patient_time ON game_sessions(patient_id, started_at);                                                                       
                                                                                                                                                                            
    -- 8. Game Results                                                                                                                                                      
    CREATE TABLE IF NOT EXISTS game_results (                                                                                                                               
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        session_id VARCHAR(36) NOT NULL UNIQUE REFERENCES game_sessions(id),                                                                                                
        event_id VARCHAR(36) NOT NULL UNIQUE,                                                                                                                               
        score INTEGER NOT NULL,                                                                                                                                             
        accuracy DOUBLE PRECISION NOT NULL,                                                                                                                                 
        response_time DOUBLE PRECISION NOT NULL,                                                                                                                            
        attempts INTEGER NOT NULL,                                                                                                                                          
        mistakes INTEGER NOT NULL DEFAULT 0,                                                                                                                                
        completed BOOLEAN NOT NULL,                                                                                                                                         
        cps DOUBLE PRECISION,                                                                                                                                               
        accuracy_component DOUBLE PRECISION,                                                                                                                                
        reaction_component DOUBLE PRECISION,                                                                                                                                
        completion_component DOUBLE PRECISION,                                                                                                                              
        consistency_component DOUBLE PRECISION,                                                                                                                             
        recommended_difficulty INTEGER,                                                                                                                                     
        recommended_activity VARCHAR(50),                                                                                                                                   
        recommendation_model VARCHAR(40),                                                                                                                                   
        recommendation_explanation TEXT,                                                                                                                                    
        caregiver_notification BOOLEAN NOT NULL DEFAULT FALSE,                                                                                                              
        recorded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC')                                                                                          
    );                                                                                                                                                                      
    CREATE INDEX IF NOT EXISTS ix_game_results_recorded_at ON game_results(recorded_at);                                                                                    
                                                                                                                                                                            
    -- 9. Reminders                                                                                                                                                         
    CREATE TABLE IF NOT EXISTS reminders (                                                                                                                                  
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        title VARCHAR(120) NOT NULL,                                                                                                                                        
        description TEXT,                                                                                                                                                   
        reminder_type VARCHAR(40) NOT NULL,                                                                                                                                 
        reminder_time VARCHAR(5) NOT NULL,                                                                                                                                  
        recurrence VARCHAR(20) NOT NULL DEFAULT 'DAILY',                                                                                                                    
        start_date DATE NOT NULL DEFAULT CURRENT_DATE,                                                                                                                      
        end_date DATE,                                                                                                                                                      
        enabled BOOLEAN NOT NULL DEFAULT TRUE,                                                                                                                              
        completed_at TIMESTAMP WITHOUT TIME ZONE                                                                                                                            
    );                                                                                                                                                                      
    CREATE INDEX IF NOT EXISTS ix_reminders_patient_id ON reminders(patient_id);                                                                                            
                                                                                                                                                                            
    -- 10. Alerts                                                                                                                                                           
    CREATE TABLE IF NOT EXISTS alerts (                                                                                                                                     
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        message TEXT NOT NULL,                                                                                                                                              
        status VARCHAR(20) NOT NULL DEFAULT 'new',                                                                                                                          
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC')                                                                                           
    );                                                                                                                                                                      
    CREATE INDEX IF NOT EXISTS ix_alerts_patient_id ON alerts(patient_id);                                                                                                  
                                                                                                                                                                            
    -- 11. Daily and Weekly Aggregates                                                                                                                                      
    CREATE TABLE IF NOT EXISTS daily_aggregates (                                                                                                                           
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        stat_date DATE NOT NULL,                                                                                                                                            
        sessions_completed INTEGER NOT NULL DEFAULT 0,                                                                                                                      
        games_played INTEGER NOT NULL DEFAULT 0,                                                                                                                            
        average_score DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                                  
        average_accuracy DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                               
        average_reaction_time DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                          
        completion_rate DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                                
        PRIMARY KEY (patient_id, stat_date)                                                                                                                                 
    );                                                                                                                                                                      
                                                                                                                                                                            
    CREATE TABLE IF NOT EXISTS weekly_aggregates (                                                                                                                          
        patient_id VARCHAR(36) NOT NULL REFERENCES patients(id),                                                                                                            
        week_start DATE NOT NULL,                                                                                                                                           
        games_played INTEGER NOT NULL DEFAULT 0,                                                                                                                            
        average_score DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                                  
        average_accuracy DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                               
        average_reaction_time DOUBLE PRECISION NOT NULL DEFAULT 0,                                                                                                          
        PRIMARY KEY (patient_id, week_start)                                                                                                                                
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- 12. Audit Logs                                                                                                                                                       
    CREATE TABLE IF NOT EXISTS audit_logs (                                                                                                                                 
        id VARCHAR(36) PRIMARY KEY,                                                                                                                                         
        user_id VARCHAR(36) REFERENCES users(id),                                                                                                                           
        action VARCHAR(120) NOT NULL,                                                                                                                                       
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC')                                                                                           
    );                                                                                                                                                                      
                                                                                                                                                                            
    -- Seed Game Catalog                                                                                                                                                    
    INSERT INTO games (game_type, display_name) VALUES                                                                                                                      
        ('MEMORY_MATCH', 'Memory Match'),                                                                                                                                   
        ('ATTENTION_TEST', 'Attention Test'),                                                                                                                               
        ('PATTERN_RECOGNITION', 'Pattern Recognition'),                                                                                                                     
        ('DAILY_ROUTINE_RECALL', 'Daily Routine Recall')                                                                                                                    
    ON CONFLICT (game_type) DO NOTHING;  