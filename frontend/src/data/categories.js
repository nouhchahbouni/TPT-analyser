export const TPT_CATEGORIES = [
  {
    id: 'grade',
    name: 'Grade',
    icon: '🎓',
    children: [
      {
        id: 'elementary',
        name: 'Elementary',
        icon: '🌱',
        children: [
          { id: 'preschool', name: 'Preschool', url: '/browse/elementary/preschool' },
          { id: 'kindergarten', name: 'Kindergarten', url: '/browse/elementary/kindergarten' },
          { id: '1st-grade', name: '1st Grade', url: '/browse/elementary/1st-grade' },
          { id: '2nd-grade', name: '2nd Grade', url: '/browse/elementary/2nd-grade' },
          { id: '3rd-grade', name: '3rd Grade', url: '/browse/elementary/3rd-grade' },
          { id: '4th-grade', name: '4th Grade', url: '/browse/elementary/4th-grade' },
          { id: '5th-grade', name: '5th Grade', url: '/browse/elementary/5th-grade' },
        ],
      },
      {
        id: 'middle-school',
        name: 'Middle School',
        icon: '🏫',
        children: [
          { id: '6th-grade', name: '6th Grade', url: '/browse/middle-school/6th-grade' },
          { id: '7th-grade', name: '7th Grade', url: '/browse/middle-school/7th-grade' },
          { id: '8th-grade', name: '8th Grade', url: '/browse/middle-school/8th-grade' },
        ],
      },
      {
        id: 'high-school',
        name: 'High School',
        icon: '🎒',
        children: [
          { id: '9th-grade', name: '9th Grade', url: '/browse/high-school/9th-grade' },
          { id: '10th-grade', name: '10th Grade', url: '/browse/high-school/10th-grade' },
          { id: '11th-grade', name: '11th Grade', url: '/browse/high-school/11th-grade' },
          { id: '12th-grade', name: '12th Grade', url: '/browse/high-school/12th-grade' },
        ],
      },
      { id: 'adult-education', name: 'Adult Education', url: '/browse/adult-education', icon: '👨‍🎓' },
    ],
  },
  {
    id: 'resource-type',
    name: 'Resource Type',
    icon: '📋',
    children: [
      {
        id: 'student-practice',
        name: 'Student Practice',
        icon: '✏️',
        children: [
          { id: 'independent-work-packet', name: 'Independent Work Packet', url: '/browse/student-practice/independent-work-packet' },
          { id: 'worksheets', name: 'Worksheets', url: '/browse/student-practice/worksheets' },
          { id: 'assessment', name: 'Assessment', url: '/browse/student-assessment/assessment' },
          { id: 'graphic-organizers', name: 'Graphic Organizers', url: '/browse/student-practice/graphic-organizers' },
          { id: 'task-cards', name: 'Task Cards', url: '/browse/student-practice/task-cards' },
          { id: 'flash-cards', name: 'Flash Cards', url: '/browse/student-practice/flash-cards' },
        ],
      },
      {
        id: 'teacher-tools',
        name: 'Teacher Tools',
        icon: '🛠️',
        children: [
          { id: 'classroom-management', name: 'Classroom Management', url: '/browse/teacher-tools/classroom-management' },
          { id: 'teacher-manuals', name: 'Teacher Manuals', url: '/browse/teacher-tools/teacher-manuals' },
          { id: 'outlines', name: 'Outlines', url: '/browse/teacher-tools/outlines' },
          { id: 'rubrics', name: 'Rubrics', url: '/browse/teacher-tools/rubrics' },
          { id: 'syllabi', name: 'Syllabi', url: '/browse/teacher-tools/syllabi' },
          { id: 'unit-plans', name: 'Unit Plans', url: '/browse/teacher-tools/unit-plans' },
          { id: 'lessons', name: 'Lessons', url: '/browse/teacher-tools/lessons' },
        ],
      },
      {
        id: 'activities',
        name: 'Activities',
        icon: '🎮',
        children: [
          { id: 'games', name: 'Games', url: '/browse/hands-on-activities/games' },
          { id: 'centers', name: 'Centers', url: '/browse/hands-on-activities/centers' },
          { id: 'projects', name: 'Projects', url: '/browse/hands-on-activities/projects' },
          { id: 'laboratory', name: 'Laboratory', url: '/browse/hands-on-activities/laboratory' },
          { id: 'songs', name: 'Songs', url: '/browse/hands-on-activities/songs' },
        ],
      },
      { id: 'clip-art', name: 'Clip Art', url: '/browse/clip-art', icon: '✂️' },
      {
        id: 'classroom-decor',
        name: 'Classroom Decor',
        icon: '🎨',
        children: [
          { id: 'bulletin-board-ideas', name: 'Bulletin Board Ideas', url: '/browse/classroom-decor/bulletin-board-ideas' },
          { id: 'posters', name: 'Posters', url: '/browse/classroom-decor/posters' },
          { id: 'word-walls', name: 'Word Walls', url: '/browse/classroom-decor/word-walls' },
        ],
      },
      { id: 'printables', name: 'Printables', url: '/browse/printables', icon: '🖨️' },
    ],
  },
  {
    id: 'seasonal',
    name: 'Seasonal',
    icon: '📅',
    children: [
      {
        id: 'holiday',
        name: 'Holiday',
        icon: '🎉',
        children: [
          { id: 'black-history-month', name: 'Black History Month', url: '/browse/holiday/black-history-month' },
          { id: 'christmas-chanukah-kwanzaa', name: 'Christmas / Chanukah / Kwanzaa', url: '/browse/holiday/christmas-chanukah-kwanzaa' },
          { id: 'earth-day', name: 'Earth Day', url: '/browse/holiday/earth-day' },
          { id: 'easter', name: 'Easter', url: '/browse/holiday/easter' },
          { id: 'halloween', name: 'Halloween', url: '/browse/holiday/halloween' },
          { id: 'hispanic-heritage-month', name: 'Hispanic Heritage Month', url: '/browse/holiday/hispanic-heritage-month' },
          { id: 'martin-luther-king-day', name: 'Martin Luther King Day', url: '/browse/holiday/martin-luther-king-day' },
          { id: 'presidents-day', name: "Presidents' Day", url: '/browse/holiday/presidents-day' },
          { id: 'st-patricks-day', name: "St. Patrick's Day", url: '/browse/holiday/st-patricks-day' },
          { id: 'thanksgiving', name: 'Thanksgiving', url: '/browse/holiday/thanksgiving' },
          { id: 'new-year', name: 'New Year', url: '/browse/holiday/new-year' },
          { id: 'valentines-day', name: "Valentine's Day", url: '/browse/holiday/valentines-day' },
          { id: 'womens-history-month', name: "Women's History Month", url: '/browse/holiday/womens-history-month' },
        ],
      },
      {
        id: 'seasonal-items',
        name: 'Seasonal',
        icon: '🍂',
        children: [
          { id: 'autumn', name: 'Autumn', url: '/browse/seasonal/autumn' },
          { id: 'winter', name: 'Winter', url: '/browse/seasonal/winter' },
          { id: 'spring', name: 'Spring', url: '/browse/seasonal/spring' },
          { id: 'summer', name: 'Summer', url: '/browse/seasonal/summer' },
          { id: 'back-to-school', name: 'Back to School', url: '/browse/seasonal/back-to-school' },
          { id: 'end-of-year', name: 'End of Year', url: '/browse/seasonal/end-of-year' },
        ],
      },
    ],
  },
  {
    id: 'ela',
    name: 'ELA',
    icon: '📖',
    children: [
      {
        id: 'ela-by-grade',
        name: 'ELA by Grade',
        icon: '🔢',
        children: [
          { id: 'preschool-ela', name: 'Preschool ELA', url: '/browse/elementary/preschool/english-language-arts' },
          { id: 'kindergarten-ela', name: 'Kindergarten ELA', url: '/browse/elementary/kindergarten/english-language-arts' },
          { id: '1st-grade-ela', name: '1st Grade ELA', url: '/browse/elementary/1st-grade/english-language-arts' },
          { id: '2nd-grade-ela', name: '2nd Grade ELA', url: '/browse/elementary/2nd-grade/english-language-arts' },
          { id: '3rd-grade-ela', name: '3rd Grade ELA', url: '/browse/elementary/3rd-grade/english-language-arts' },
          { id: '4th-grade-ela', name: '4th Grade ELA', url: '/browse/elementary/4th-grade/english-language-arts' },
          { id: '5th-grade-ela', name: '5th Grade ELA', url: '/browse/elementary/5th-grade/english-language-arts' },
          { id: '6th-grade-ela', name: '6th Grade ELA', url: '/browse/middle-school/6th-grade/english-language-arts' },
          { id: '7th-grade-ela', name: '7th Grade ELA', url: '/browse/middle-school/7th-grade/english-language-arts' },
          { id: '8th-grade-ela', name: '8th Grade ELA', url: '/browse/middle-school/8th-grade/english-language-arts' },
          { id: 'high-school-ela', name: 'High School ELA', url: '/browse/high-school/english-language-arts' },
        ],
      },
      {
        id: 'elementary-ela',
        name: 'Elementary ELA',
        icon: '🌱',
        children: [
          { id: 'ela-reading', name: 'Reading', url: '/browse/elementary/english-language-arts/reading' },
          { id: 'ela-writing', name: 'Writing', url: '/browse/elementary/english-language-arts/writing' },
          { id: 'phonics', name: 'Phonics & Phonological Awareness', url: '/browse/elementary/english-language-arts/phonics-and-phonological-awareness' },
          { id: 'ela-vocabulary', name: 'Vocabulary', url: '/browse/elementary/english-language-arts/vocabulary' },
          { id: 'grammar', name: 'Grammar', url: '/browse/elementary/english-language-arts/grammar' },
          { id: 'spelling', name: 'Spelling', url: '/browse/elementary/english-language-arts/spelling' },
          { id: 'poetry', name: 'Poetry', url: '/browse/elementary/english-language-arts/poetry' },
          { id: 'ela-test-prep-elem', name: 'ELA Test Prep', url: '/browse/elementary/english-language-arts/ela-test-prep' },
        ],
      },
      {
        id: 'middle-school-ela',
        name: 'Middle School ELA',
        icon: '🏫',
        children: [
          { id: 'ms-ela-literature', name: 'Literature', url: '/browse/middle-school/english-language-arts/literature' },
          { id: 'ms-ela-informational', name: 'Informational Text', url: '/browse/middle-school/english-language-arts/informational-text' },
          { id: 'ms-ela-writing', name: 'Writing', url: '/browse/middle-school/english-language-arts/writing' },
          { id: 'ms-ela-creative-writing', name: 'Creative Writing', url: '/browse/middle-school/english-language-arts/creative-writing' },
          { id: 'ms-ela-essays', name: 'Writing Essays', url: '/browse/middle-school/english-language-arts/writing-essays' },
          { id: 'ms-ela-test-prep', name: 'ELA Test Prep', url: '/browse/middle-school/english-language-arts/ela-test-prep' },
        ],
      },
      {
        id: 'high-school-ela',
        name: 'High School ELA',
        icon: '🎒',
        children: [
          { id: 'hs-ela-literature', name: 'Literature', url: '/browse/high-school/english-language-arts/literature' },
          { id: 'hs-ela-informational', name: 'Informational Text', url: '/browse/high-school/english-language-arts/informational-text' },
          { id: 'hs-ela-writing', name: 'Writing', url: '/browse/high-school/english-language-arts/writing' },
          { id: 'hs-ela-creative-writing', name: 'Creative Writing', url: '/browse/high-school/english-language-arts/creative-writing' },
          { id: 'hs-ela-essays', name: 'Writing Essays', url: '/browse/high-school/english-language-arts/writing-essays' },
          { id: 'hs-ela-test-prep', name: 'ELA Test Prep', url: '/browse/high-school/english-language-arts/ela-test-prep' },
        ],
      },
    ],
  },
  {
    id: 'math',
    name: 'Math',
    icon: '📐',
    children: [
      {
        id: 'math-by-grade',
        name: 'Math by Grade',
        icon: '🔢',
        children: [
          { id: 'preschool-math', name: 'Preschool Math', url: '/browse/elementary/preschool/math' },
          { id: 'kindergarten-math', name: 'Kindergarten Math', url: '/browse/elementary/kindergarten/math' },
          { id: '1st-grade-math', name: '1st Grade Math', url: '/browse/elementary/1st-grade/math' },
          { id: '2nd-grade-math', name: '2nd Grade Math', url: '/browse/elementary/2nd-grade/math' },
          { id: '3rd-grade-math', name: '3rd Grade Math', url: '/browse/elementary/3rd-grade/math' },
          { id: '4th-grade-math', name: '4th Grade Math', url: '/browse/elementary/4th-grade/math' },
          { id: '5th-grade-math', name: '5th Grade Math', url: '/browse/elementary/5th-grade/math' },
          { id: '6th-grade-math', name: '6th Grade Math', url: '/browse/middle-school/6th-grade/math' },
          { id: '7th-grade-math', name: '7th Grade Math', url: '/browse/middle-school/7th-grade/math' },
          { id: '8th-grade-math', name: '8th Grade Math', url: '/browse/middle-school/8th-grade/math' },
          { id: 'high-school-math', name: 'High School Math', url: '/browse/high-school/math' },
        ],
      },
      {
        id: 'elementary-math',
        name: 'Elementary Math',
        icon: '🌱',
        children: [
          { id: 'basic-operations', name: 'Basic Operations', url: '/browse/elementary/math/basic-operations' },
          { id: 'numbers', name: 'Numbers', url: '/browse/elementary/math/numbers' },
          { id: 'geometry-elem', name: 'Geometry', url: '/browse/elementary/math/geometry' },
          { id: 'measurement', name: 'Measurement', url: '/browse/elementary/math/measurement' },
          { id: 'mental-math', name: 'Mental Math', url: '/browse/elementary/math/mental-math' },
          { id: 'place-value', name: 'Place Value', url: '/browse/elementary/math/place-value' },
          { id: 'arithmetic', name: 'Arithmetic', url: '/browse/elementary/math/arithmetic' },
          { id: 'fractions-elem', name: 'Fractions', url: '/browse/elementary/math/fractions' },
          { id: 'decimals-elem', name: 'Decimals', url: '/browse/elementary/math/decimals' },
          { id: 'math-test-prep-elem', name: 'Math Test Prep', url: '/browse/elementary/math/math-test-prep' },
        ],
      },
      {
        id: 'middle-school-math',
        name: 'Middle School Math',
        icon: '🏫',
        children: [
          { id: 'ms-algebra', name: 'Algebra', url: '/browse/middle-school/math/algebra' },
          { id: 'ms-basic-operations', name: 'Basic Operations', url: '/browse/middle-school/math/basic-operations' },
          { id: 'ms-decimals', name: 'Decimals', url: '/browse/middle-school/math/decimals' },
          { id: 'ms-fractions', name: 'Fractions', url: '/browse/middle-school/math/fractions' },
          { id: 'ms-geometry', name: 'Geometry', url: '/browse/middle-school/math/geometry' },
          { id: 'ms-math-test-prep', name: 'Math Test Prep', url: '/browse/middle-school/math/math-test-prep' },
        ],
      },
      {
        id: 'high-school-math',
        name: 'High School Math',
        icon: '🎒',
        children: [
          { id: 'hs-algebra', name: 'Algebra', url: '/browse/high-school/math/algebra' },
          { id: 'hs-algebra-2', name: 'Algebra 2', url: '/browse/high-school/math/algebra-2' },
          { id: 'hs-geometry', name: 'Geometry', url: '/browse/high-school/math/geometry' },
          { id: 'hs-math-test-prep', name: 'Math Test Prep', url: '/browse/high-school/math/math-test-prep' },
          { id: 'statistics', name: 'Statistics', url: '/browse/high-school/math/statistics' },
          { id: 'precalculus', name: 'Precalculus', url: '/browse/high-school/math/precalculus' },
          { id: 'calculus', name: 'Calculus', url: '/browse/high-school/math/calculus' },
        ],
      },
    ],
  },
  {
    id: 'science',
    name: 'Science',
    icon: '🔬',
    children: [
      {
        id: 'science-by-grade',
        name: 'Science by Grade',
        icon: '🔢',
        children: [
          { id: 'preschool-science', name: 'Preschool Science', url: '/browse/elementary/preschool/science' },
          { id: 'kindergarten-science', name: 'Kindergarten Science', url: '/browse/elementary/kindergarten/science' },
          { id: '1st-grade-science', name: '1st Grade Science', url: '/browse/elementary/1st-grade/science' },
          { id: '2nd-grade-science', name: '2nd Grade Science', url: '/browse/elementary/2nd-grade/science' },
          { id: '3rd-grade-science', name: '3rd Grade Science', url: '/browse/elementary/3rd-grade/science' },
          { id: '4th-grade-science', name: '4th Grade Science', url: '/browse/elementary/4th-grade/science' },
          { id: '5th-grade-science', name: '5th Grade Science', url: '/browse/elementary/5th-grade/science' },
          { id: '6th-grade-science', name: '6th Grade Science', url: '/browse/middle-school/6th-grade/science' },
          { id: '7th-grade-science', name: '7th Grade Science', url: '/browse/middle-school/7th-grade/science' },
          { id: '8th-grade-science', name: '8th Grade Science', url: '/browse/middle-school/8th-grade/science' },
          { id: 'high-school-science', name: 'High School Science', url: '/browse/high-school/science' },
        ],
      },
      {
        id: 'science-by-topic',
        name: 'Science by Topic',
        icon: '🧪',
        children: [
          { id: 'astronomy', name: 'Astronomy', url: '/browse/science/astronomy' },
          { id: 'biology', name: 'Biology', url: '/browse/science/biology' },
          { id: 'chemistry', name: 'Chemistry', url: '/browse/science/chemistry' },
          { id: 'earth-sciences', name: 'Earth Sciences', url: '/browse/science/earth-sciences' },
          { id: 'physics', name: 'Physics', url: '/browse/science/physics' },
          { id: 'physical-science', name: 'Physical Science', url: '/browse/science/physical-science' },
        ],
      },
    ],
  },
  {
    id: 'social-studies',
    name: 'Social Studies',
    icon: '🌍',
    children: [
      {
        id: 'social-studies-by-grade',
        name: 'Social Studies by Grade',
        icon: '🔢',
        children: [
          { id: 'preschool-ss', name: 'Preschool', url: '/browse/elementary/preschool/social-studies' },
          { id: 'kindergarten-ss', name: 'Kindergarten', url: '/browse/elementary/kindergarten/social-studies' },
          { id: '1st-grade-ss', name: '1st Grade', url: '/browse/elementary/1st-grade/social-studies' },
          { id: '2nd-grade-ss', name: '2nd Grade', url: '/browse/elementary/2nd-grade/social-studies' },
          { id: '3rd-grade-ss', name: '3rd Grade', url: '/browse/elementary/3rd-grade/social-studies' },
          { id: '4th-grade-ss', name: '4th Grade', url: '/browse/elementary/4th-grade/social-studies' },
          { id: '5th-grade-ss', name: '5th Grade', url: '/browse/elementary/5th-grade/social-studies' },
          { id: '6th-grade-ss', name: '6th Grade', url: '/browse/middle-school/6th-grade/social-studies' },
          { id: '7th-grade-ss', name: '7th Grade', url: '/browse/middle-school/7th-grade/social-studies' },
          { id: '8th-grade-ss', name: '8th Grade', url: '/browse/middle-school/8th-grade/social-studies' },
          { id: 'high-school-ss', name: 'High School', url: '/browse/high-school/social-studies' },
        ],
      },
      {
        id: 'social-studies-by-topic',
        name: 'Social Studies by Topic',
        icon: '📜',
        children: [
          { id: 'ancient-history', name: 'Ancient History', url: '/browse/social-studies/ancient-history' },
          { id: 'economics', name: 'Economics', url: '/browse/social-studies/economics' },
          { id: 'european-history', name: 'European History', url: '/browse/social-studies/european-history' },
          { id: 'government', name: 'Government', url: '/browse/social-studies/government' },
          { id: 'geography', name: 'Geography', url: '/browse/social-studies/geography' },
          { id: 'native-americans', name: 'Native Americans', url: '/browse/social-studies/native-americans' },
          { id: 'middle-ages', name: 'Middle Ages', url: '/browse/social-studies/middle-ages' },
          { id: 'psychology', name: 'Psychology', url: '/browse/social-studies/psychology' },
          { id: 'us-history', name: 'US History', url: '/browse/social-studies/us-history' },
          { id: 'world-history', name: 'World History', url: '/browse/social-studies/world-history' },
        ],
      },
    ],
  },
  {
    id: 'languages',
    name: 'Languages',
    icon: '🌐',
    children: [
      { id: 'asl', name: 'American Sign Language', url: '/browse/world-languages/american-sign-language' },
      { id: 'arabic', name: 'Arabic', url: '/browse/world-languages/arabic' },
      { id: 'chinese', name: 'Chinese', url: '/browse/world-languages/chinese' },
      { id: 'french', name: 'French', url: '/browse/world-languages/french' },
      { id: 'german', name: 'German', url: '/browse/world-languages/german' },
      { id: 'italian', name: 'Italian', url: '/browse/world-languages/italian' },
      { id: 'japanese', name: 'Japanese', url: '/browse/world-languages/japanese' },
      { id: 'latin', name: 'Latin', url: '/browse/world-languages/latin' },
      { id: 'portuguese', name: 'Portuguese', url: '/browse/world-languages/portuguese' },
      { id: 'spanish', name: 'Spanish', url: '/browse/world-languages/spanish' },
    ],
  },
  {
    id: 'arts',
    name: 'Arts',
    icon: '🎭',
    children: [
      {
        id: 'visual-arts',
        name: 'Arts',
        icon: '🎨',
        children: [
          { id: 'art-history', name: 'Art History', url: '/browse/art/art-history' },
          { id: 'graphic-arts', name: 'Graphic Arts', url: '/browse/art/graphic-arts' },
          { id: 'visual-arts-sub', name: 'Visual Arts', url: '/browse/art/visual-arts' },
          { id: 'other-arts', name: 'Other Arts', url: '/browse/art/other-arts' },
        ],
      },
      {
        id: 'performing-arts',
        name: 'Performing Arts',
        icon: '🎵',
        children: [
          { id: 'dance', name: 'Dance', url: '/browse/performing-arts/dance' },
          { id: 'drama', name: 'Drama', url: '/browse/performing-arts/drama' },
          { id: 'instrumental-music', name: 'Instrumental Music', url: '/browse/performing-arts/instrumental-music' },
          { id: 'music', name: 'Music', url: '/browse/performing-arts/music' },
          { id: 'music-composition', name: 'Music Composition', url: '/browse/performing-arts/music-composition' },
          { id: 'vocal-music', name: 'Vocal Music', url: '/browse/performing-arts/vocal-music' },
        ],
      },
    ],
  },
  {
    id: 'special-education',
    name: 'Special Education',
    icon: '⭐',
    children: [
      { id: 'special-ed', name: 'Special Education', url: '/browse/special-education' },
      { id: 'speech-therapy', name: 'Speech Therapy', url: '/browse/speech-therapy' },
    ],
  },
  {
    id: 'social-emotional',
    name: 'Social Emotional',
    icon: '💚',
    children: [
      { id: 'character-education', name: 'Character Education', url: '/browse/social-emotional/character-education' },
      { id: 'classroom-community', name: 'Classroom Community', url: '/browse/social-emotional/classroom-community' },
      { id: 'school-counseling', name: 'School Counseling', url: '/browse/social-emotional/school-counseling' },
      { id: 'school-psychology', name: 'School Psychology', url: '/browse/social-emotional/school-psychology' },
      { id: 'sel', name: 'Social Emotional Learning', url: '/browse/social-emotional/social-emotional-learning' },
    ],
  },
  {
    id: 'specialty',
    name: 'Specialty',
    icon: '🔧',
    children: [
      { id: 'cte', name: 'Career & Technical Education', url: '/browse/specialty/career-and-technical-education' },
      { id: 'child-care', name: 'Child Care', url: '/browse/specialty/child-care' },
      { id: 'coaching', name: 'Coaching', url: '/browse/specialty/coaching' },
      { id: 'cooking', name: 'Cooking', url: '/browse/specialty/cooking' },
      { id: 'health', name: 'Health', url: '/browse/health' },
      { id: 'life-skills', name: 'Life Skills', url: '/browse/special-education/life-skills' },
      { id: 'occupational-therapy', name: 'Occupational Therapy', url: '/browse/specialty/occupational-therapy' },
      { id: 'physical-education', name: 'Physical Education', url: '/browse/physical-education' },
      { id: 'physical-therapy', name: 'Physical Therapy', url: '/browse/specialty/physical-therapy' },
      { id: 'professional-development', name: 'Professional Development', url: '/browse/specialty/professional-development' },
      { id: 'service-learning', name: 'Service Learning', url: '/browse/specialty/service-learning' },
      { id: 'vocational-education', name: 'Vocational Education', url: '/browse/specialty/vocational-education' },
    ],
  },
]

// Flatten all leaf categories (those with a url)
export function getAllLeafCategories() {
  const leaves = []
  function traverse(nodes, parents = []) {
    for (const node of nodes) {
      if (node.url) {
        leaves.push({ ...node, breadcrumb: [...parents, node.name] })
      }
      if (node.children) {
        traverse(node.children, [...parents, node.name])
      }
    }
  }
  traverse(TPT_CATEGORIES)
  return leaves
}

// Find a category by id anywhere in the tree
export function findCategoryById(id) {
  function search(nodes) {
    for (const node of nodes) {
      if (node.id === id) return node
      if (node.children) {
        const found = search(node.children)
        if (found) return found
      }
    }
    return null
  }
  return search(TPT_CATEGORIES)
}
