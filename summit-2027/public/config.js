window.SUMMIT_CONFIG = {
  dates: ['2027-01-11', '2027-01-12', '2027-01-13'],
  logo: "/assets/gp27.png", // Add the supplied logo URL or /logo.png. Brand colours are provisional.
  colors: { pink: '#ef87b5', red: '#bd1622' },
  hotel: { name: 'ROBINSON Fleesensee', address: 'Penkower Straße 2, 17213 Göhren-Lebbin, Germany', website: 'https://www.robinson.com/en/en/resort-holiday/germany/fleesensee/club-details/' },
  // Replace pending content with confirmed summit arrangements, not standard hotel inclusions.
  food: [ {name:'Breakfast',detail:'Summit inclusion to be confirmed'}, {name:'Lunch & dinner',detail:'Summit inclusion to be confirmed'}, {name:'Drinks & coffee',detail:'Included selection and bar arrangements to be confirmed'} ],
  arrival: 'Meeting points, shuttle times and check-in arrangements will be shared here.',
  departure: 'Return transfers, luggage storage and the summit check-out time will be shared here.',
  contacts: [{name:'Thai',role:'Your summit contact',photo:null,email:null,phone:null},{name:'Katie',role:'Your summit contact',photo:null,email:null,phone:null}],
  speakers: [], // {name, role, company, bio, photo, linkedin}; use verified LinkedIn URLs.
  teams: Array.from({length:10},(_,i)=>({id:i+1,name:`Team ${String(i+1).padStart(2,'0')}`,members:[]})),
  // Team videos and release times live in backend/content.json, so locked URLs are not exposed.
};
