// Demo data for the scheme-finder replica. Eligibility rules are simplified for the demo;
// links point to the real scheme pages on myScheme.
window.SCHEMES = [
  { name: "Indira Gandhi National Old Age Pension Scheme", slug: "ignoaps", benefit: "Monthly pension of ₹200–₹500 for senior citizens from BPL households.", minAge: 60, maxIncome: 100000 },
  { name: "Atal Pension Yojana", slug: "apy", benefit: "Guaranteed pension of ₹1,000–₹5,000 a month after age 60.", minAge: 18, maxAge: 40 },
  { name: "Ayushman Bharat – PM Jan Arogya Yojana", slug: "ab-pmjay", benefit: "Free hospital treatment up to ₹5 lakh per family per year.", maxIncome: 250000 },
  { name: "Ayushman Vay Vandana (PM-JAY for 70+)", slug: "ab-pmjay", benefit: "Free health cover up to ₹5 lakh a year for everyone aged 70 or above.", minAge: 70 },
  { name: "Pradhan Mantri Ujjwala Yojana", slug: "pmuy", benefit: "Free LPG connection for women from poor households.", genders: ["female"], minAge: 18, maxIncome: 100000 },
  { name: "Sukanya Samriddhi Yojana", slug: "ssy", benefit: "High-interest savings account for a girl child's education and marriage.", genders: ["female"], maxAge: 10 },
  { name: "Pradhan Mantri Suraksha Bima Yojana", slug: "pmsby", benefit: "Accident insurance of ₹2 lakh for ₹20 a year.", minAge: 18, maxAge: 70 },
  { name: "Pradhan Mantri Jeevan Jyoti Bima Yojana", slug: "pmjjby", benefit: "Life insurance of ₹2 lakh for ₹436 a year.", minAge: 18, maxAge: 50 },
  { name: "PM Kisan Samman Nidhi", slug: "pm-kisan", benefit: "₹6,000 a year in three instalments for farmer families.", minAge: 18 },
  { name: "Pradhan Mantri Awas Yojana – Gramin", slug: "pmay-g", benefit: "Financial help to build a pucca house in rural areas.", minAge: 18, maxIncome: 300000 },
  { name: "Pradhan Mantri Matru Vandana Yojana", slug: "pmmvy", benefit: "₹5,000+ cash support for pregnant and nursing mothers.", genders: ["female"], minAge: 19, maxAge: 45 },
  { name: "PM SVANidhi", slug: "pm-svanidhi", benefit: "Collateral-free working-capital loan for street vendors.", minAge: 18, maxAge: 65 },
  { name: "Stand-Up India", slug: "sui", benefit: "Bank loans of ₹10 lakh–₹1 crore for women and SC/ST entrepreneurs.", genders: ["female"], minAge: 18 },
  { name: "National Scheme for Persons with Disabilities Pension (IGNDPS)", slug: "igndps", benefit: "Monthly pension for persons with severe disabilities from BPL households.", minAge: 18, maxIncome: 100000 },
  { name: "Indira Gandhi National Widow Pension Scheme", slug: "ignwps", benefit: "Monthly pension for widows aged 40 and above from BPL households.", genders: ["female"], minAge: 40, maxIncome: 100000 },
  { name: "Pradhan Mantri Shram Yogi Maan-dhan", slug: "pm-sym", benefit: "₹3,000 monthly pension after 60 for unorganised workers.", minAge: 18, maxAge: 40, maxIncome: 180000 },
  { name: "Senior Citizens Savings Scheme", slug: "scss", benefit: "Safe savings scheme with quarterly interest for people aged 60+.", minAge: 60 },
  { name: "Mukhyamantri Ladli Behna Yojana", slug: "mmlby", benefit: "₹1,250 a month for women in Madhya Pradesh.", genders: ["female"], minAge: 21, maxAge: 60, states: ["madhya_pradesh"], maxIncome: 250000 },
  { name: "Mukhyamantri Kanya Sumangala Yojana", slug: "mksy", benefit: "₹25,000 in stages for girls in Uttar Pradesh.", genders: ["female"], maxAge: 18, states: ["uttar_pradesh"], maxIncome: 300000 },
  { name: "Kalaignar Magalir Urimai Thogai", slug: "kmut", benefit: "₹1,000 a month for women heads of family in Tamil Nadu.", genders: ["female"], minAge: 21, states: ["tamil_nadu"], maxIncome: 250000 },
  { name: "Majhi Ladki Bahin Yojana", slug: "mmmlby", benefit: "₹1,500 a month for women in Maharashtra.", genders: ["female"], minAge: 21, maxAge: 65, states: ["maharashtra"], maxIncome: 250000 },
  { name: "Delhi Old Age Pension", slug: "oaps-delhi", benefit: "₹2,000–₹2,500 a month for senior citizens in Delhi.", minAge: 60, states: ["delhi"], maxIncome: 100000 },
  { name: "Post Matric Scholarship for SC Students", slug: "pms-sc", benefit: "Scholarship covering fees and allowance for higher studies.", minAge: 15, maxAge: 30, maxIncome: 250000 },
  { name: "PM Vishwakarma", slug: "pm-vishwakarma", benefit: "Training, toolkit and cheap loans for traditional artisans.", minAge: 18 },
  { name: "Transgender Persons Welfare (SMILE)", slug: "smile", benefit: "Skill training, health and shelter support for transgender persons.", genders: ["transgender"], minAge: 18 }
];
