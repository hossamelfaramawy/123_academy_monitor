/**
 * 123 Academy - Modular Quiz Parser & Curriculum Loader
 * 
 * This script isolates the complexity of loading subject configs,
 * fetching split JSON letter files, and generating spaced-repetition quizzes.
 */

// Helper: Map skill ID to individual letter JSON filename
// e.g. "english_3_s1" -> "letter_a.json", "english_3_s2" -> "letter_b.json"
function getLetterFileName(skillId) {
    const match = skillId.match(/english_3_s(\d+)/i);
    if (match) {
        const idx = parseInt(match[1]) - 1;
        if (idx >= 0 && idx < 26) {
            const letter = String.fromCharCode(97 + idx); // 97 is 'a'
            return `letter_${letter}.json`;
        }
    }
    return null;
}

// Helper: Shuffle array in place
function shuffleArray(array) {
    const arr = [...array];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
}

/**
 * Loads the subject configuration and builds the quiz questions.
 * 
 * @param {string} skillId - The active skill ID (e.g. "english_3_s3")
 * @returns {Promise<Object>} Resolves to { questions, activeLevelData, quizConfig }
 */
function loadQuizEngine(skillId) {
    const subject = skillId.split('_')[0] || 'english';
    const configPath = `subjects/${subject}/quiz_config.json`;
    
    console.log(`[QuizParser] Loading subject config from: ${configPath}`);
    
    return fetch(configPath)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch config at ${configPath}`);
            }
            return response.json();
        })
        .then(config => {
            const sequence = config.sequence || [];
            const currentIdx = sequence.indexOf(skillId);
            
            // Determine files to fetch based on subject loader type
            const promises = [];
            const isEnglish = (subject === 'english');
            
            if (isEnglish) {
                // English: split curriculum (fetch active + review files)
                // 1. Fetch active letter
                const activeFile = getLetterFileName(skillId) || 'letter_a.json';
                promises.push(
                    fetch(`subjects/english/curriculum/${activeFile}`)
                        .then(res => res.json())
                        .then(data => ({ type: 'active', data }))
                );
                
                // 2. Fetch past review letters in sequence
                if (currentIdx > 0) {
                    const reviewCount = config.review_questions_count || 2;
                    // Get up to reviewCount preceding skill IDs
                    const startIdx = Math.max(0, currentIdx - reviewCount);
                    const reviewSkills = sequence.slice(startIdx, currentIdx);
                    
                    reviewSkills.forEach(revSkillId => {
                        const revFile = getLetterFileName(revSkillId);
                        if (revFile) {
                            promises.push(
                                fetch(`subjects/english/curriculum/${revFile}`)
                                    .then(res => {
                                        if (res.ok) return res.json();
                                        return {};
                                    })
                                    .then(data => ({ type: 'review', data }))
                            );
                        }
                    });
                }
            } else {
                // Arabic / Math: Single global JSON file
                let fileSuffix = 'eng';
                if (subject === 'arabic') fileSuffix = 'ar';
                else if (subject === 'math') fileSuffix = 'math';
                
                const globalPath = `subjects/${subject}/${fileSuffix}_curriculum.json`;
                promises.push(
                    fetch(globalPath)
                        .then(res => res.json())
                        .then(data => ({ type: 'global', data }))
                );
            }
            
            return Promise.all(promises).then(results => {
                let curriculum = {};
                let activeLevelData = null;
                let reviewQuestionsPool = [];
                
                results.forEach(res => {
                    if (res.type === 'active' || res.type === 'global') {
                        curriculum = Object.assign(curriculum, res.data);
                        activeLevelData = res.data[skillId];
                    } else if (res.type === 'review') {
                        curriculum = Object.assign(curriculum, res.data);
                        // Add review questions to the pool
                        const skillData = Object.values(res.data)[0];
                        if (skillData && skillData.questions) {
                            reviewQuestionsPool = reviewQuestionsPool.concat(skillData.questions);
                        }
                    }
                });
                
                // Fallback active level data if not resolved
                if (!activeLevelData) {
                    // Try to resolve first available key in loaded curriculum
                    const keys = Object.keys(curriculum);
                    activeLevelData = curriculum[skillId] || (keys.length > 0 ? curriculum[keys[0]] : null);
                }
                
                if (!activeLevelData) {
                    throw new Error(`Curriculum data for skill ${skillId} could not be resolved.`);
                }
                
                // 3. Build Spaced Repetition Quiz questions list
                let selectedQuestions = [];
                const activeQuestions = activeLevelData.questions || [];
                
                // Determine slice sizes from config
                const currentCount = config.current_skill_questions_count || 3;
                const reviewCount = config.review_questions_count || 2;
                
                // If there are no past reviews possible (first week)
                if (currentIdx <= 0 || reviewQuestionsPool.length === 0) {
                    // Take questions from active level (up to total_questions)
                    selectedQuestions = shuffleArray(activeQuestions).slice(0, config.total_questions || 5);
                } else {
                    // Spaced Repetition combination:
                    const currentSelected = shuffleArray(activeQuestions).slice(0, currentCount);
                    const reviewSelected = shuffleArray(reviewQuestionsPool).slice(0, reviewCount);
                    
                    selectedQuestions = currentSelected.concat(reviewSelected);
                    
                    // Shuffle the final combined list if config requires it
                    if (config.order === 'random') {
                        selectedQuestions = shuffleArray(selectedQuestions);
                    }
                }
                
                console.log(`[QuizParser] Built quiz successfully. Total: ${selectedQuestions.length} questions.`);
                
                return {
                    questions: selectedQuestions,
                    activeLevelData: activeLevelData,
                    quizConfig: config
                };
            });
        });
}
