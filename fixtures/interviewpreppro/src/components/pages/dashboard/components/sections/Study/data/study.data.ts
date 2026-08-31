import {
GraduationCap,
Building2, // For university choice - represents institution
ScrollText, // For academic background - represents transcripts/documents
Wallet, // For financial support - represents money/funding
Users, // For family background - represents family/relationships
Landmark, // For ties to home - represents country/national ties
Flag,
Plane,
Info
} from 'lucide-react';
import { StudyCategory } from '../types/study.types';

export const visaInterviewPrepCategories: StudyCategory[] = [
{
id: 'academic-plans',
title: 'Your Study Goals',
icon: GraduationCap,
description: 'Why you chose to study in the US and what you want to achieve'
},
{
id: 'university-choice',
title: 'Why This School?',
icon: Building2,
description: 'Show you did your homework on picking the perfect university'
},
{
id: 'academic-background',
title: 'Your Academic Story',
icon: ScrollText,
description: 'Present your grades and achievements with confidence'
},
{
id: 'financial-support',
title: 'Money Matters',
icon: Wallet,
description: 'Prove you can afford your education without stress'
},
{
id: 'family-background',
title: 'Your Family',
icon: Users,
description: 'Talk about your family naturally and positively'
},
{
id: 'ties-to-home',
title: 'Coming Back Home',
icon: Landmark,
description: 'Show strong reasons why you\'ll return after graduation'
},
{
id: 'future-plans',
title: 'After Graduation',
icon: Flag,
description: "Your career dreams and how your US degree fits into them. This isn't about having everything figured out - it's about showing you've thought about your future and how your education will help you achieve your goals back home."
},
{
id: 'visa-travel-history',
title: 'Your Travel Story',
icon: Plane,
description: "Any trips you've taken or visas you've applied for before. Don't worry if you haven't traveled much - everyone starts somewhere! If you have traveled, just be honest about where you went and that you followed the rules."
},
{
id: "general-tips",
title: "Interview Day Success",
icon: Info,
description: "The insider secrets to nailing your interview. Remember, most F-1 interviews are super quick (2-5 minutes!), so being prepared and confident makes all the difference. Think of it as a brief conversation where you get to share your exciting plans.",
},
];

export const visaInterviewPrepContent = {
"academic-plans": {
title: "Your Study Goals",
icon: "graduation-cap",
description: "Here's where you get to shine by talking about your passion for learning and why the US is the perfect place for your education. The visa officer wants to see that you're genuinely excited about studying (not just trying to get to America for other reasons).",
sampleQuestions: [
  "Why do you want to study in the United States?",
  "What will you study, and why did you pick that major?",
  "Why not just study in your home country instead?",
  "Tell me about your high school - where did you go?",
  "How will studying in the US help your future?"
],
howToAnswer: [
  {
    title: "Share What Excites You About US Education",
    content: "This is your moment to geek out a little! Talk about what genuinely drew you to US universities - maybe it's the research opportunities, the diverse student body, or specific programs that aren't available back home. For example: 'I chose the US because American universities are known for hands-on learning and cutting-edge research. Plus, I love that I can explore different subjects before declaring my major - that flexibility isn't offered in my country.' Show you've done your research and aren't just following a trend."
  },
  {
    title: "Connect Your Major to Your Passions",
    content: "Don't just say 'Computer Science is popular.' Instead, tell your story: 'I've loved coding since I built my first website in 10th grade, and I want to study CS because I dream of creating apps that solve real problems in my community.' Connect your choice to your experiences, interests, or things you've already done. The officer wants to see genuine interest, not just someone picking a random major."
  },
  {
    title: "Acknowledge Your Home Country (But Show Why US is Better for You)",
    content: "When they ask why you're not studying at home, be respectful but specific. You might say: 'While my country has good universities, the specific program I want - like interactive media design - is much more developed in the US. American schools also offer internship opportunities and industry connections that will really help my career.' Focus on opportunities and quality, not putting down your home country."
  },
  {
    title: "Show You're Serious About Being a Student",
    content: "Make it clear that studying is your #1 priority. You could say: 'I believe education is the foundation for everything I want to achieve. Getting my degree is essential before I start my career because I want to be really well-prepared.' This shows the officer you're entering the US with the right intentions - to learn, not to work illegally or immigrate."
  },
  {
    title: "Address the 'Why Now?' Question",
    content: "If they ask why you're starting college now (especially if you took a gap year), have a clear answer: 'I spent last year working and saving money for college, which made me even more motivated to study.' Or 'I used my gap year to improve my English and research universities - now I'm totally ready for this next step.' Show that any delays were purposeful, not because you're unsure about education."
  },
  {
    title: "Handle Questions About Alternative Paths",
    content: "Sometimes they ask why you're not working instead of studying. Be ready: 'While I could get a job now, I believe getting a proper education first will open many more doors for my career. I want to build a strong foundation of knowledge before entering the workforce.' This shows maturity and long-term thinking."
  },
  {
    title: "Demonstrate Knowledge of US Education System",
    content: "Show you understand what you're getting into: 'I'm excited about the American system where I can take electives outside my major and participate in research projects. The focus on critical thinking and class discussions will really help me grow as a student.' This proves you've researched beyond just university rankings."
  },
  {
    title: "Connect to Global Perspective",
    content: "Mention how studying with international students appeals to you: 'I'm looking forward to learning alongside students from all over the world. That global perspective will be valuable when I return home to work in international business.' This shows you value the cultural exchange aspect, not just the degree."
  }
]
},
"university-choice": {
title: "Why This School?",
icon: "landmark",
description: "Time to show off your research skills! The officer wants to see that you chose your university thoughtfully, not just because it was the only one that accepted you. Even if it was your safety school, focus on what you genuinely like about it.",
sampleQuestions: [
  "Why did you choose this specific university?",
  "How many schools did you apply to? How many accepted you?",
  "If other schools rejected you, why do you think that happened?",
  "What made you pick this school over your other options?",
  "Where is your university located? What do you know about that area?"
],
howToAnswer: [
  {
    title: "Show You Did Your Homework",
    content: "Get specific about what attracted you to this school. Maybe say: 'I chose State University because they have an amazing robotics lab, small class sizes where I can actually talk to professors, and their co-op program will give me real work experience.' Or mention a specific professor whose research excites you, a unique program feature, or even the campus culture. The more specific you are, the more it shows you researched carefully rather than applying randomly."
  },
  {
    title: "Be Honest About Your Application Journey",
    content: "If you applied to multiple schools, just be straightforward: 'I applied to six universities and got accepted to three. I chose this one because it offered the best combination of academic quality and financial aid.' If you only got into one school, that's totally fine too! Focus on why you're excited about it: 'This was actually my top choice because of their excellent engineering program and supportive international student community.'"
  },
  {
    title: "Know Your School's Location and Show Enthusiasm",
    content: "Do some basic research on your university's city or state. You might say: 'My school is in Austin, Texas - I'm excited to experience the tech scene there and the music culture.' Or 'It's in a college town in Ohio, which means everything revolves around students and there's a real sense of community.' You don't need to be an expert, but show you've thought about where you'll be living for four years."
  },
  {
    title: "If You Had Multiple Options, Explain Your Choice",
    content: "If you got into several schools, explain your decision-making process: 'I also got into University X, but I chose this one because of their better career services and the scholarship they offered.' If this was your only acceptance, pivot to what excites you: 'I'm actually thrilled because this school has exactly what I'm looking for - great professors and hands-on learning opportunities.'"
  },
  {
    title: "Mention Specific Programs or Opportunities",
    content: "Reference unique features of your university: 'They have a study abroad program in Japan which aligns perfectly with my interest in international business.' Or 'Their makerspace has 3D printers and laser cutters that I can't wait to use for my engineering projects.' This shows you've looked beyond just rankings and really understand what makes your school special."
  },
  {
    title: "Address Ranking Questions Smartly",
    content: "If your school isn't highly ranked, focus on fit: 'While it might not be the most famous university, it has exactly what I need - small classes, great professors, and strong industry connections in my field.' Don't apologize for your choice; instead, show you prioritized the right factors for YOUR education and goals."
  },
  {
    title: "Know Key Facts About Your University",
    content: "Be ready with basic details: student population, when it was founded, notable alumni, or academic strengths. For example: 'It's a mid-size university with about 15,000 students, founded in 1875, and it's known for producing successful engineers.' This level of knowledge shows genuine interest and preparation."
  },
  {
    title: "Connect School Choice to Your Future Goals",
    content: "Link your university to your career plans: 'I chose this school because their alumni network is strong in renewable energy companies, which is exactly where I want to work after graduation.' Or 'Their entrepreneurship center will help me develop the business skills I need to start my own company someday.' Show this choice supports your long-term vision."
  },
  {
    title: "Handle Questions About Rejections Gracefully",
    content: "If asked about schools that rejected you, stay positive: 'I applied to some reach schools like MIT, but I'm honestly excited about where I'm going because it's a better fit for what I want to study.' Never criticize schools that rejected you - instead, frame your chosen school as the perfect match for your needs."
  },
  {
    title: "Show You've Connected with the School Community",
    content: "Mention any interactions you've had: 'I attended their virtual information session and loved talking to current students about their experiences.' Or 'I've been following their engineering department on social media and I'm excited about the projects students are working on.' This demonstrates ongoing engagement, not just a one-time application."
  }
]
},
"academic-background": {
title: "Your Academic Story",
icon: "file-text",
description: "This is where you prove you can handle US college coursework. The officer wants to see that you're academically prepared and won't struggle with English or the academic workload. It's not about being perfect - it's about being prepared.",
sampleQuestions: [
  "What were your SAT/ACT scores?",
  "What was your high school GPA?",
  "How's your English? Can you handle classes taught in English?",
  "Can I see your transcripts or diploma?",
  "Are you ready for the American education system?"
],
howToAnswer: [
  {
    title: "State Your Numbers Confidently",
    content: "Know your test scores by heart and say them with confidence: 'I scored 1350 on the SAT and 7.0 on IELTS. My high school GPA was 3.7.' Even if your scores aren't perfect, own them! The fact that you got admitted means your university believes you can succeed. If a score is lower than you'd like, you can briefly add: 'I'm really motivated to do well in college and I've been working hard to improve my English skills.'"
  },
  {
    title: "Show English Confidence",
    content: "Your TOEFL/IELTS scores prove your English ability, so reference them: 'My IELTS score of 7.5 shows I can handle academic English, and I've been practicing by reading American news and watching lectures online.' You can also mention any English classes you've taken or American TV shows you watch. The key is showing you're comfortable communicating in English, not just passing a test."
  },
  {
    title: "Highlight Academic Achievements (Without Bragging)",
    content: "If you have honors, awards, or challenging courses, mention them naturally: 'I was in my school's honor society and took advanced math classes.' Or 'I won second place in our regional science fair.' You're not bragging - you're showing evidence that you take academics seriously and have a track record of success."
  },
  {
    title: "Have Your Documents Ready",
    content: "Keep your transcripts, test scores, and diploma organized in a folder. If the officer asks to see them, hand them over smoothly and say: 'Here are my official transcripts' or 'This is my high school diploma.' Being organized shows you're prepared and professional. It's also a chance to demonstrate that everything you've said is backed up by real documents."
  },
  {
    title: "Show You're Ready for New Challenges",
    content: "If asked about adapting to American education, be positive: 'I know American classrooms encourage more discussion and participation, and I'm actually excited about that. I like sharing ideas and learning from classmates with different backgrounds.' Show that you've thought about the differences and you're eager to adapt, not scared of them."
  },
  {
    title: "Address Any Academic Weaknesses Honestly",
    content: "If you have lower grades in certain subjects, be prepared to explain: 'My math grades weren't as strong, but I've been taking extra tutoring and I'm much more confident now.' Or 'I struggled with chemistry, but since I'm majoring in literature, I've focused my energy on improving my writing skills.' Show growth and self-awareness."
  },
  {
    title: "Demonstrate Continuous Learning",
    content: "Show you're still preparing: 'I've been taking online courses to get ahead in my major' or 'I've been reading academic papers in my field to prepare for college-level research.' This proves you're serious about succeeding and already thinking like a college student."
  },
  {
    title: "Know Your Class Rank and Context",
    content: "If your school provides class rank, know it: 'I graduated 15th out of 200 students.' If your school is competitive, mention that: 'My school is known for rigorous academics - we send about 80% of graduates to university.' This gives context to your performance and shows you came from a serious academic environment."
  },
  {
    title: "Handle Questions About Study Methods",
    content: "Be ready to explain how you plan to succeed: 'I'm a very organized student - I use planners and study groups. I also know the university has tutoring services and study abroad programs that I want to take advantage of.' Show you've thought about HOW you'll succeed, not just that you will."
  },
  {
    title: "Address Any Gaps in Education",
    content: "If you took time off or had interruptions, explain clearly: 'I had to pause my education for a year to help with family finances, but during that time I worked and gained real-world experience that made me even more motivated to study.' Frame any gaps as learning experiences or necessary steps."
  },
  {
    title: "Show Knowledge of Academic Support Systems",
    content: "Demonstrate you've researched help available: 'I know my university has a writing center and ESL support programs. I plan to use these resources to make sure I succeed academically.' This shows maturity and planning, plus awareness that success requires effort and support."
  }
]
},
"financial-support": {
title: "Money Matters",
icon: "dollar-sign",
description: "This is crucial - you need to prove you can afford your entire education without working illegally in the US. The officer wants to see that you have a solid financial plan and won't become a burden on the US system or drop out due to money problems.",
sampleQuestions: [
  "How will you pay for your education?",
  "Who's helping you pay for school? What's your relationship to them?",
  "What does your sponsor do for work? How much do they earn?",
  "How much is your tuition? Can you cover all expenses?",
  "Do you plan to work while studying?"
],
howToAnswer: [
  {
    title: "Break Down Your Financial Plan Clearly",
    content: "Be specific with numbers: 'My parents have saved $60,000 which covers two years of tuition and living expenses. We also have $25,000 in additional savings, and I received a $8,000 scholarship from the university.' Show you've done the math and can cover your ENTIRE program. Never say something like 'I'll figure it out' or 'I'll find a job' - that's a huge red flag since F-1 students can't work off-campus."
  },
  {
    title: "Explain Who's Supporting You and Why",
    content: "Be clear about your sponsor: 'My father is my sponsor. He owns a small business and has been saving for my education for years because he believes in investing in my future.' Or 'My parents are both teachers and they've been putting money aside specifically for my college education.' Show this is a planned investment, not a financial strain that might leave you stranded."
  },
  {
    title: "Share Your Sponsor's Financial Stability",
    content: "Give context about your sponsor's ability to pay: 'My mother works as a hospital administrator and earns about $40,000 per year. She also has savings and owns our family home.' You want to show that supporting your education isn't going to bankrupt your family. If you have bank statements or financial documents, be ready to show them if asked."
  },
  {
    title: "Emphasize School Over Work",
    content: "When asked about working, focus on academics: 'My priority is my studies, and my family is covering my expenses so I won't need to work off-campus. I know F-1 students can only work on-campus for up to 20 hours, and I might consider that later if it doesn't interfere with my grades.' This shows you know the rules and aren't planning to work illegally."
  },
  {
    title: "Have Financial Proof Ready",
    content: "Keep bank statements, scholarship letters, and financial affidavits organized. If the officer asks for proof, confidently say: 'Yes, I have my family's bank statements and my scholarship letter right here.' Having documentation ready shows you're prepared and everything you've said is legitimate. Don't volunteer documents unless asked, but be ready to provide them."
  },
  {
    title: "Address Scholarships and Financial Aid",
    content: "If you received scholarships, explain them clearly: 'I received a merit scholarship worth $10,000 per year because of my academic performance. This covers about 25% of my tuition costs.' If you got need-based aid, explain the process: 'The university reviewed my family's finances and offered need-based aid to help make education affordable.' Show you earned these awards through legitimate means."
  },
  {
    title: "Handle Questions About Family Sacrifice",
    content: "If asked whether your family is struggling to pay, be honest but reassuring: 'My parents are making sacrifices because they believe education is important, but this won't put us in debt or create hardship. They've been planning and saving for this for years.' Show it's a thoughtful investment, not a desperate gamble."
  },
  {
    title: "Know the Total Cost Breakdown",
    content: "Be ready to break down expenses: 'Tuition is $35,000 per year, living expenses are about $15,000, so I need roughly $50,000 annually. My family has budgeted for the full four years.' Include housing, food, books, health insurance, and personal expenses. This shows you understand the real cost of studying abroad."
  },
  {
    title: "Address Currency Exchange and Transfer Plans",
    content: "Show you've thought about practical money matters: 'My family will transfer money through our bank, and I'll open a US bank account when I arrive. We've already factored in exchange rates and transfer fees in our budget.' This demonstrates real planning, not just wishful thinking."
  },
  {
    title: "Handle Multiple Funding Sources",
    content: "If you have various funding sources, organize them clearly: 'My funding comes from three sources: $40,000 from my parents' savings, $20,000 from my grandmother's education fund, and $5,000 yearly from my merit scholarship. Together, this covers my entire program.' Make it easy for the officer to understand your financial picture."
  },
  {
    title: "Address Emergency Fund Questions",
    content: "Show you've planned for unexpected costs: 'Beyond tuition and living expenses, my family has set aside an additional $10,000 for emergencies or unexpected costs. We want to make sure I can focus on studying without financial stress.' This demonstrates thorough preparation and family commitment."
  },
  {
    title: "Handle Questions About Part-Time Work",
    content: "If they ask about campus jobs, show you understand the rules: 'I might look for an on-campus job like working in the library, but only if it doesn't hurt my studies. I know the 20-hour limit and that off-campus work isn't allowed without special permission.' Demonstrate knowledge of F-1 work restrictions."
  }
]
},
"family-background": {
title: "Your Family",
icon: "users",
description: "The officer wants to understand your family situation - both to see your support system and to check if you have strong ties back home. If you have family in the US, don't worry! Just be honest and show that your purpose is studying, not joining family permanently.",
sampleQuestions: [
  "What do your parents do for work?",
  "Do you have brothers or sisters? What do they do?",
  "Do you have any family or friends living in the US?",
  "Who will take care of things at home while you're studying?",
  "Will anyone from your family visit you in the US?"
],
howToAnswer: [
  {
    title: "Describe Your Parents' Work Simply",
    content: "Just give clear, straightforward answers: 'My dad is a mechanical engineer at a manufacturing company, and my mom teaches middle school math.' Or 'My father runs a small restaurant, and my mother is a nurse at the local hospital.' You don't need lots of details - just show your family has stable employment and you're proud of what they do."
  },
  {
    title: "Share About Your Siblings Naturally",
    content: "If you have siblings, mention what they're up to: 'I have an older sister who's a doctor and a younger brother still in high school.' If all your siblings are in your home country, that actually helps show you have family ties bringing you back. If a sibling is abroad or in the US, just be honest but emphasize your own plans to return home."
  },
  {
    title: "Be Honest About US Connections",
    content: "If you have relatives or friends in the US, always tell the truth: 'Yes, my uncle lives in California, but I'll be studying in New York and we probably won't see each other much.' Or simply 'No, I don't have any family in the US - I'll be experiencing everything for the first time!' Having family in the US isn't automatically bad, but show that you're focused on studying, not moving to be near relatives."
  },
  {
    title: "Show Strong Family Support and Ties",
    content: "Emphasize that your family supports your education and expects you back: 'My parents are so excited for me to gain this experience, and they're counting on me to come back and help with our family business.' Or 'My family has always valued education, and they know I'll return with knowledge that can benefit our community.' This shows you have people waiting for you at home."
  },
  {
    title: "Address Family Business or Responsibilities",
    content: "If your family has a business, mention your future role: 'My parents own a construction company, and they're excited for me to bring back modern engineering knowledge to help expand the business.' Or 'My family has farming land, and I want to use my agricultural studies to introduce sustainable farming methods.' Show how your education benefits your family's future."
  },
  {
    title: "Handle Questions About Family Visits",
    content: "Be prepared for questions about family visiting you: 'My parents might visit for my graduation, but they're focused on supporting me from home right now.' Or 'My family understands that studying abroad is expensive, so we're prioritizing my education costs over travel.' Show your family is supportive but realistic about priorities."
  },
  {
    title: "Discuss Family Education Background",
    content: "Share your family's attitude toward education: 'Both my parents went to university, so they understand how important higher education is.' Or 'I'll be the first in my family to get a university degree, which makes my parents incredibly proud and motivated to support me.' Connect your education to your family's values and dreams."
  },
  {
    title: "Address Being an Only Child (If Applicable)",
    content: "If you're an only child, frame it positively: 'Being an only child means my parents have been able to focus their resources on my education, and I feel a responsibility to make the most of this opportunity.' Show how this creates stronger ties, not weaker ones, and emphasize your eventual return to care for aging parents."
  },
  {
    title: "Handle Divorced or Complex Family Situations",
    content: "If you have divorced parents or complex family situations, keep it simple: 'My parents are divorced, but they both support my education. My mother is my primary sponsor.' Don't over-explain personal details - just show that your support system is stable and committed to your success."
  },
  {
    title: "Show Family Cultural Values",
    content: "Connect to cultural expectations: 'In our culture, education is highly valued, and my family sees my US degree as bringing honor to our family name.' Or 'My parents believe that knowledge should be used to serve our community, so they expect me to return and contribute to our country's development.' This reinforces your intention to return home."
  }
]
},
"ties-to-home": {
title: "Coming Back Home",
icon: "house",
description: "This is probably the most important category. The officer needs to believe you'll return home after graduation - it's actually a legal requirement for F-1 visas. You need to convince them you have compelling reasons to go back and that the US is just a temporary stop for your education.",
sampleQuestions: [
  "Will you return to your home country after graduation?",
  "What are your plans after you finish your degree?",
  "Are you sure you won't try to stay in the US permanently?",
  "What will bring you back home after your studies?",
  "Will you visit home during school breaks?"
],
howToAnswer: [
  {
    title: "Say 'Yes' Confidently and Give Reasons",
    content: "Be definitive: 'Absolutely, I will return home. My goal is to use my US education to start a tech company in my country, where there's huge potential in the growing digital market.' Or 'Yes, definitely. I want to come back and work in renewable energy, which is a big focus in my government right now.' Don't be wishy-washy - show you have clear plans that require you to be back home."
  },
  {
    title: "Highlight What's Waiting for You at Home",
    content: "Talk about your connections: 'All my family is back home, and I'm very close to them. I also have friends starting businesses that I'd love to join.' Or mention opportunities: 'My country is investing heavily in infrastructure, which is perfect for my civil engineering degree.' Maybe even mention property: 'My family owns land that I'll eventually help manage.' Show you have a life to return to."
  },
  {
    title: "Connect Your Future to Your Home Country",
    content: "Paint a picture of your future: 'After graduation, I want to work for a few years to gain experience, then start my own consulting firm back home.' Or 'I plan to join my father's business and help expand it using what I've learned about international markets.' Show that your US education is part of a plan that leads back home, not away from it."
  },
  {
    title: "Address the Immigration Question Directly",
    content: "If pressed about staying in the US, be clear: 'I understand the concern, but my roots and my future are in my home country. The US is giving me an amazing education, but home is where I want to build my career and eventually raise a family.' Show you understand this is temporary and you respect the visa requirements."
  },
  {
    title: "Show You'll Stay Connected to Home",
    content: "Mention plans to visit: 'I definitely plan to go home during summer breaks to spend time with family and maybe do internships there.' This shows you're not cutting ties with home and you're thinking of your US experience as temporary. It also demonstrates you can afford round-trip travel, which is another good sign."
  },
  {
    title: "Reference Economic Opportunities at Home",
    content: "Show knowledge of your home country's growth: 'My country's economy is growing rapidly, especially in technology and healthcare, which creates great opportunities for someone with my education.' Or 'The government is investing in green energy projects, and I want to be part of that development.' Demonstrate that going home means joining exciting opportunities, not missing out on them."
  },
  {
    title: "Mention Property or Assets at Home",
    content: "If applicable, reference tangible ties: 'My family owns our home and some property that I'll eventually inherit and manage.' Or 'We have a family business that's been operating for 20 years - I want to help take it to the next level.' Physical assets show concrete reasons to return."
  },
  {
    title: "Address Cultural and Personal Ties",
    content: "Emphasize personal connections: 'I'm very close to my grandparents and want to be near them as they age.' Or 'I have a long-term relationship with someone back home, and we plan to build our future there together.' Show that your heart and personal life are anchored at home."
  },
  {
    title: "Discuss Contributing to National Development",
    content: "Frame your return in terms of service: 'I want to use my education to help develop my country's infrastructure' or 'My goal is to train other engineers back home using modern techniques I'll learn in the US.' Show you see yourself as bringing valuable knowledge back to benefit your nation."
  },
  {
    title: "Handle Questions About Brain Drain",
    content: "If asked about talented people leaving your country, flip it positively: 'That's exactly why I'm committed to returning - my country needs people with international education to stay and help build a better future. I don't want to be part of the brain drain; I want to be part of the solution.' Show you've thought about this responsibility."
  },
  {
    title: "Address Professional Licensing or Certification",
    content: "If relevant to your field, mention professional requirements: 'To practice engineering in my country, I need to get licensed there, which requires working domestically.' Or 'My goal is to eventually teach at universities back home, which requires me to understand our local education system.' Show practical reasons that require your physical presence at home."
  },
  {
    title: "Show Understanding of Home Country Advantages",
    content: "Demonstrate that you see benefits of your home country: 'The cost of living is much lower at home, so my salary will go further.' Or 'There's less competition in my field back home, which means more opportunities for leadership roles.' Show you've realistically compared and still choose home."
  }
]
},
"future-plans": {
title: "After Graduation",
icon: "flag",
description: "Here's where you paint a picture of your exciting future! The officer wants to see that you have direction and ambition, and that your US degree is a stepping stone toward goals back home. You don't need to have everything figured out, but show you've thought about how your education will help your career.",
sampleQuestions: [
  "What do you want to do after you graduate?",
  "Do you have a specific career goal in mind?",
  "Where do you see yourself in 5-10 years?",
  "Do you want to pursue graduate school after your bachelor's?",
  "What kind of job do you hope to get with your degree?"
],
howToAnswer: [
  {
    title: "Paint a Clear Picture of Your Career Dreams",
    content: "Be specific about your goals: 'I want to become a software engineer at a tech company in my home country, maybe something like our version of Google.' Or 'My dream is to work in sustainable agriculture and help farmers in my region use modern technology.' Having a clear vision shows you're motivated and that your US education has purpose beyond just getting a degree."
  },
  {
    title: "Connect Everything Back to Home",
    content: "Always tie your plans to your home country: 'I'm excited to bring back what I learn about renewable energy because my country is just starting to invest in solar power.' Or 'I want to use my business degree to help modernize my family's company and maybe expand to neighboring countries.' This shows the officer that your future success depends on being back home."
  },
  {
    title: "Show Realistic Short and Long-term Thinking",
    content: "Break down your timeline: 'Right after graduation, I want to get some experience working for an established company back home. In 5-10 years, I'd love to start my own firm or maybe go into business with college friends.' This shows maturity and realistic planning. Avoid saying you're unsure - even if you are, focus on the possibilities that excite you."
  },
  {
    title: "Focus on Growth, Not Immigration",
    content: "Frame everything around personal and professional development: 'My US education will give me the technical skills and global perspective I need to really make an impact in my field back home.' Avoid any language that suggests you might stay in the US. Instead, show how your American experience will make you more valuable and successful in your home country."
  },
  {
    title: "Address Graduate School Plans",
    content: "If considering further study, tie it to career goals: 'I might pursue a master's degree eventually, but I want to get some work experience first to understand what specialization would be most valuable.' Or 'I plan to work for a few years, then maybe return to school for an MBA to help me start my own business.' Show graduate school as part of a bigger plan, not uncertainty about the future."
  },
  {
    title: "Mention Specific Industries or Companies",
    content: "Reference real opportunities at home: 'I'd love to work for companies like [specific company names in your country] that are leading innovation in my field.' Or 'My country's [specific industry] sector is growing rapidly, and I want to be part of that expansion.' This shows you've researched actual opportunities, not just dreaming vaguely."
  },
  {
    title: "Show Understanding of Market Needs",
    content: "Demonstrate knowledge of gaps you could fill: 'There's a shortage of engineers with international experience in my country, especially in green technology.' Or 'My country is developing its digital infrastructure, which creates opportunities for people with my computer science background.' Show you'll return to meet real demand."
  },
  {
    title: "Address Entrepreneurship Ambitions",
    content: "If you want to start a business, explain the advantage of being home: 'I want to start a consulting firm that helps local businesses adopt sustainable practices - this would be much more relevant and impactful in my home market than trying to compete in the saturated US market.' Show why home is better for your entrepreneurial goals."
  },
  {
    title: "Handle Questions About Job Market Challenges",
    content: "If pressed about economic challenges at home, stay positive: 'While the job market is competitive, that's exactly why people with international education are so valuable. My US degree will give me an advantage in finding good opportunities.' Frame challenges as reasons why your education makes you more valuable."
  },
  {
    title: "Connect to National Development Goals",
    content: "Reference your country's development priorities: 'My government is investing heavily in renewable energy, and I want to be part of that transition.' Or 'My country is working to improve healthcare infrastructure, which aligns perfectly with my biomedical engineering studies.' Show your goals align with national priorities."
  },
  {
    title: "Address Optional Practical Training (OPT) Carefully",
    content: "If asked about working in the US after graduation, be strategic: 'I know about OPT, and I might use it to gain some practical experience, but my long-term plans are definitely back home. Any US work experience would just make me more valuable when I return.' Frame any potential US work as temporary skill-building, not a path to staying."
  },
  {
    title: "Show Knowledge of Industry Trends",
    content: "Demonstrate you understand where your field is heading: 'Artificial intelligence is becoming huge in my country's banking sector, and I want to be part of developing those systems.' Or 'My country is moving toward sustainable farming practices, which is perfect timing for my agricultural engineering degree.' Show you're returning to opportunities, not limitations."
  }
]
},
"visa-travel-history": {
title: "Your Travel Story",
icon: "plane",
description: "Don't stress if you haven't traveled much - plenty of students get their F-1 visa without extensive travel history! The officer just wants to know about any previous trips or visa applications, and most importantly, that you followed the rules when you did travel.",
sampleQuestions: [
  "Have you been to the United States before?",
  "Is this your first time traveling internationally?",
  "What other countries have you visited?",
  "Have you applied for a US visa before?",
  "Has any country ever denied you a visa?"
],
howToAnswer: [
  {
    title: "Be Straightforward About US Travel",
    content: "If you've been to the US before, briefly explain: 'Yes, I visited with my family in 2019 for two weeks. We went to Disney World and New York City, and I returned home on time.' Or if you haven't: 'No, this will be my first time in the US, and I'm really excited to experience it!' The key is showing that if you did visit before, you followed the rules and left when you were supposed to."
  },
  {
    title: "Share Your Travel Experience (Or Lack Thereof)",
    content: "If you've traveled: 'I've been to Thailand and Singapore with my family for vacations, and I went to South Korea for a student exchange program.' If you haven't: 'I haven't had the chance to travel internationally yet, but I'm excited that studying abroad will be my first big adventure!' Both answers are totally fine - just be honest."
  },
  {
    title: "Always Be Honest About Previous Applications",
    content: "If you've applied for visas before, mention them: 'I got a tourist visa for the UK last year to visit my cousin.' If you've been denied: 'I applied for a US tourist visa two years ago but was denied. I think it was because I was younger and didn't have strong ties to home then, but now I have university admission and clear study plans.' Don't hide denials - the officer can see your history anyway."
  },
  {
    title: "Emphasize Rule-Following",
    content: "Whether you've traveled or not, show you understand visa rules: 'Whenever I've traveled, I've always made sure to return before my visa expired.' Or if you're new to travel: 'I understand how important it is to follow visa rules, and I will absolutely respect the terms of my student visa.' This shows you're responsible and trustworthy."
  },
  {
    title: "Address Previous US Visits in Detail",
    content: "If you've been to the US before, be ready with specifics: 'I visited in summer 2020 with my family. We stayed for 10 days, visited Disneyland and San Francisco, and I left on the exact date on my return ticket.' Mention what you did, how long you stayed, and emphasize that you followed all the rules. If you overstayed even by accident, be honest and explain the circumstances."
  },
  {
    title: "Handle Visa Denial History Positively",
    content: "If you've been denied any visa before, acknowledge it and show growth: 'I was denied a tourist visa to Canada two years ago. Looking back, I think I didn't clearly explain my travel plans and ties to home. Since then, I've gained more life experience and now have a clear purpose for international travel - my education.' Show you've learned and matured."
  },
  {
    title: "Discuss Travel for Educational Purposes",
    content: "If you've traveled for school trips or exchanges, highlight these: 'I went to Germany for a month-long language immersion program through my high school. It was amazing to experience different cultures, and I returned home exactly when the program ended.' Educational travel shows you're serious about learning and following program rules."
  },
  {
    title: "Address Limited Travel Due to Financial Reasons",
    content: "If you haven't traveled much due to cost, be honest: 'My family focused on saving money for my education rather than vacations, but I've always dreamed of experiencing different cultures. That's part of why I'm so excited about studying in the US.' Frame it as prioritizing education over leisure travel."
  },
  {
    title: "Handle Questions About Transit or Short Stops",
    content: "If you've had layovers or transit stops in the US, mention them: 'I had a layover in Chicago airport when flying to Canada, but I didn't leave the airport.' Even brief technical 'entries' should be mentioned to show complete honesty. The officer will appreciate your thoroughness."
  },
  {
    title: "Show Knowledge of Immigration Rules",
    content: "Demonstrate understanding of the system: 'I know that visitor visas and student visas have different purposes and requirements. My previous tourist trips were just for vacation, but now I have a specific educational goal that requires a student visa.' Show you understand different visa categories and their purposes."
  },
  {
    title: "Address Family Travel History",
    content: "If your family travels frequently but you don't, explain: 'My parents travel for business, but I've focused on my studies. Now that I'm older and have clear educational goals, I'm ready for my own international experience.' Show this is the right time in your life for international education."
  },
  {
    title: "Handle Questions About Future Travel Plans",
    content: "If asked about other countries you want to visit, connect it back to education: 'After I finish my degree, I'd love to travel more, but right now my focus is completely on my studies. I want to make the most of my time in the US for educational purposes.' Keep the focus on education, not tourism."
  }
]
},
"general-tips": {
title: "Interview Day Success",
icon: "info",
description: "The big day is here! Remember, most F-1 interviews are super short (2-5 minutes), so every moment counts. Think of it as a quick conversation where you get to share your exciting plans, not an interrogation. Here's how to nail it:",
sampleQuestions: [],  // General tips category does not have specific interview questions
howToAnswer: [
  {
    title: "Dress Like You Mean Business (But Not Too Fancy)",
    content: "Think 'meeting your partner's parents' level of dress - neat, respectful, but not over the top. A collared shirt or nice blouse with dress pants or a modest skirt works great. Avoid anything too casual (like flip-flops or wrinkled clothes) or too formal (like a full suit unless that's normal in your culture). Clean, pressed clothes and good grooming show you're taking this seriously. Skip strong perfume or flashy jewelry - you want the focus on your words, not your outfit."
  },
  {
    title: "Be Confident, Friendly, and Respectful",
    content: "Walk in with a smile and a friendly 'Good morning!' Make eye contact when you speak - it shows confidence and honesty. It's totally normal to be nervous (your heart might be racing!), but try to channel that energy into enthusiasm about your plans. Speak clearly and at a normal pace. If you don't understand a question, it's perfectly fine to say 'Could you please repeat that?' Stay calm even if the officer seems serious - they're just doing their job, not trying to intimidate you."
  },
  {
    title: "Give Direct, Honest Answers (Keep It Short!)",
    content: "Answer exactly what they ask in 1-2 sentences, then stop. Don't ramble or volunteer extra information unless they ask for it. For example, if they ask 'What will you study?' say 'Computer Science' not a 5-minute speech about your entire academic journey. Be honest even if you think your answer isn't perfect - visa officers can spot lies from a mile away. If you don't know something, it's better to admit it than to make something up."
  },
  {
    title: "Know Your Stuff Cold",
    content: "Review everything in your application the night before - your university name, location, program length, tuition costs, test scores, family details, etc. You should be able to answer basic questions without thinking. Practice saying your key points out loud so they flow naturally. If the officer asks to see documents, you should be able to find them in seconds. Know your story so well that you can tell it confidently even when you're nervous."
  },
  {
    title: "Organize Your Documents Like a Pro",
    content: "Use a folder or envelope to keep everything neat: passport, appointment confirmation, DS-160 confirmation page, I-20, transcripts, test scores, financial documents, and any photos or certificates. Arrange them in the order you're most likely to need them. When an officer asks for something, hand it over smoothly and say 'Here's my transcript' or whatever they requested. Being organized shows you're responsible and prepared."
  },
  {
    title: "Practice, But Don't Sound Rehearsed",
    content: "Do mock interviews with friends or family, or even practice in front of a mirror. Focus on the key points you want to make, but don't memorize exact scripts - you want to sound natural, not like you're reciting a speech. Practice until you feel comfortable talking about your plans, but leave room for genuine conversation. The officer wants to see the real you, not a perfectly rehearsed performance."
  },
  {
    title: "Listen Carefully and Stay Focused",
    content: "Pay attention to exactly what the officer is asking. If they ask about your finances, talk about money, not your academic plans. Don't try to sneak in information they didn't ask for - it can make you seem evasive or like you're not listening. If you're not sure what they want, ask for clarification rather than guessing. Stay engaged and present in the conversation."
  },
  {
    title: "Keep It Positive and Stay Cool",
    content: "Maintain a positive attitude throughout the interview, even if you get tough questions. Never argue with the officer or get defensive - they're not your enemy, they're just doing their job. If they point out something concerning (like low test scores), acknowledge it briefly and redirect to your strengths. If things don't go as expected, stay respectful. Remember, confidence and a positive attitude can make up for a lot of other concerns."
  },
  {
    title: "Mind Your Body Language",
    content: "Stand up straight, keep your hands relaxed (not fidgeting), and maintain good eye contact. Don't lean on the counter or slouch - it can look disrespectful or overly casual. Occasional nodding shows you're engaged and listening. Keep your hands visible and avoid touching your face or hair too much, which can make you look nervous or dishonest. Your body language should match your confident words."
  },
  {
    title: "Arrive Early and Handle the Logistics",
    content: "Get to the embassy or consulate at least 30 minutes early to account for security lines and unexpected delays. Rushing in last-minute will spike your anxiety and hurt your performance. Check what you can and can't bring inside (usually no phones or electronics), and plan accordingly. Bring a water bottle if allowed - nerves can make your mouth dry. Getting the logistics right lets you focus completely on the interview itself."
  },
  {
    title: "Handle Nerves and Anxiety Effectively",
    content: "It's completely normal to be nervous - the officer expects it! Use deep breathing techniques: breathe in for 4 counts, hold for 4, breathe out for 4. This actually calms your nervous system. If your hands shake, that's okay - just keep them steady when handing over documents. If your voice wavers at first, that's normal too. Remember: being nervous doesn't hurt your chances, but being unprepared does."
  },
  {
    title: "Prepare for Technical Difficulties",
    content: "Sometimes computers crash or systems go down during interviews. Stay patient and positive if there are delays. Use any waiting time to review your key points mentally, but don't over-rehearse and psych yourself out. If the officer has to reschedule due to technical issues, be understanding - it's not a reflection on your application."
  },
  {
    title: "Know What NOT to Bring Up",
    content: "Don't volunteer information about wanting to work in the US long-term, political opinions, criticism of your home country, personal problems, or anything negative about the US immigration system. Keep the conversation focused on your education and positive future plans. Let the officer guide the conversation - answer what they ask, don't steer toward topics you want to discuss."
  },
  {
    title: "Handle Unexpected or Difficult Questions",
    content: "If you get a curveball question, take a moment to think before answering. It's okay to say 'That's a great question, let me think for a second.' Don't panic if you don't know something - admit it honestly: 'I'm not sure about that specific detail, but I can tell you that...' Then pivot to something you do know well. Stay calm and truthful rather than trying to bluff your way through."
  },
  {
    title: "Prepare for Different Interview Styles",
    content: "Some officers are very friendly and chatty, others are more formal and serious. Don't let the officer's style throw you off - adapt your energy to match theirs while staying authentic. If they're serious, be respectful and professional. If they're friendly, you can be a bit more relaxed, but always maintain respect. The interview style doesn't predict the outcome."
  },
  {
    title: "End on a Strong Note",
    content: "When the interview ends, thank the officer politely: 'Thank you for your time.' Don't ask about the decision or when you'll hear back - they'll tell you if you need to know anything. If they say they need additional documents, ask clearly what you need to provide and by when. Leave with the same confidence you came in with, regardless of how you think it went."
  },
  {
    title: "Have a Backup Plan",
    content: "Know what you'll do if your visa is denied. This doesn't mean expecting denial, but being prepared shows maturity. You might defer admission for a year to strengthen your application, apply to universities in your home country, or address whatever issues caused the denial. Having a plan helps you stay calm because you know denial isn't the end of the world."
  },
  {
    title: "Understand the Decision Timeline",
    content: "Most decisions are made immediately, but sometimes additional processing is needed. If your passport is kept for 'administrative processing,' this doesn't mean denial - it just means they need more time to review something. Stay patient and don't contact the embassy repeatedly asking for updates. If you need your passport for other travel, let them know, but understand their timeline takes priority."
  }
]
}
}