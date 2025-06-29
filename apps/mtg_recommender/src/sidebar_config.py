TYPES = [
    'Creature', 'Planeswalker', 'Battle', 'Artifact', 'Enchantment', 'Instant', 'Sorcery', 
    'Land', 'Kindred', 'Tribal', 'Stickers', 'Summon', 
]

SUPERTYPES = ['Basic', 'Host', 'Legendary', 'Ongoing', 'Snow', 'World']

SUBTYPES = [
    'Abian', 'Adventure', 'Advisor', 'Aetherborn', 'Ajani', 'Alara', 'Alfava Metraxis', 'Alicorn', 'Alien',
    'Ally','Aminatou','Amonkhet','Amsterdam','Androzani Minor','Angel','Angrath','Antausia','Antelope','Apalapucia',
    'Ape','Arcane','Arcavios','Archer','Archon','Arkhos','Arlinn','Armadillo','Armored','Art','Artificer','Artist',
    'Ashiok','Assassin','Assembly-Worker','Astartes','Athlete','Atog','Attraction','Aura','Aurochs','Autobot','Avatar',
    'Avishkar','Azgol','Azra','B.O.B.','Background','Baddest,','Badger','Bahamut','Barbarian','Bard','Basilisk','Basri','Bat',
    'Bear','Beast','Beaver','Beeble','Beholder','Belenon','Berserker','Biggest,','Bird','Blind Eternities','Bloomburrow','Boar',
    'Bobblehead','Bolas',"Bolas's Meditation Realm",'Boxer','Brainiac','Bringer','Brushwagg','Bureaucrat','Byode',"C'tan",
    'Calix','Camel','Capenna','Capybara','Carrier','Cartouche','Case','Cat','Cave','Centaur','Cephalid','Chameleon','Champion',
    'Chandra','Chef','Chicago','Chicken','Child','Chimera','Chorus','Citizen','Clamfolk','Clamhattan','Class','Cleric','Cloud',
    'Clown','Clue','Cockatrice','Comet','Construct','Contraption','Control','Cow','Coward','Coyote','Crab','Cridhe','Crocodile','Curse','Custodes','Cyberman',
    'Cyborg','Cyclops','Dack','Dakkon','Dalek','Daretti','Darillium','Dauthi','Davriel','Deb','Deer','Demigod','Demon','Desert','Designer','Detective',
    'Devil','Dihada','Dinosaur','Djinn','Doctor','Dog','Dominaria','Domri','Donkey','Dovin','Dragon','Drake','Dreadnought','Drone','Druid','Dryad',
    'Duck','Dungeon','Duskmourn','Dwarf','Earth','Echoir','Efreet','Egg','Elder','Eldraine','Eldrazi','Elemental','Elemental?','Elephant','Elf','Elk',
    'Ellywick','Elminster','Elspeth','Elves','Employee','Equilor','Equipment','Ergamon','Ersta','Estrid','Etiquette','Eye','Fabacin','Faerie','Ferret','Fiora',
    'Fire','Fish','Flagbearer','Foldaria','Food','Forest','Fortification','Foundations','Fox','Fractal','Freyalise','Frog','Fungus','Gallifrey','Gamer','Gargantikar',
    'Gargoyle','Garruk','Gate','Giant','Gideon','Gith','Glimmer','Gnoll','Gnome','Goat','Gobakhan','Goblin','God','Golem','Gorgon','Grandchild',
    'Gremlin','Griffin','Grist','Guest','Guff','Gus','Hag','Halfling','Hamster','Harpy','Hatificer','Hawk','Head','Hell','Hellion','Hero','Hippo',
    'Hippogriff','Homarid','Homunculus','Horror','Horse','Horsehead Nebula','Huatli','Human','Human?','Hydra','Hyena','Igpay','Ikoria','Illusion','Imp','Incarnation',
    'Innistrad','Inquisitor','Insect','Inzerva','Iquatana','Ir','Island','Ixalan','Jace','Jackal','Jared','Jaya','Jellyfish','Jeska','Judge','Juggernaut',
    'Kaito','Kaldheim','Kamigawa','Kandoka','Kangaroo','Karn','Karsus','Kasmina','Kavu','Kaya','Kephalai','Key','Killbot','Kinshala','Kiora','Kirin',
    'Kithkin','Knight','Kobold','Kolbahan','Kor','Koth','Kraken','Kylem','Kyneth','LaIR','Lady','Lair','Lamia','Lammasu','Las Vegas','Leech',
    'Lesson','Leviathan','Lhurgoyf','Licid','Liliana','Lizard','Lobster','Locus','Lolth','Lorwyn','Lukka','Luvion','Luxior','MagicCon','Mammoth','Manticore',
    'Mars','Master','Masticore','Mercadia','Mercenary','Merfolk','Metathran','Mime','Mine','Minion','Minotaur','Minsc','Mirrodin','Mission','Mite','Moag',
    'Mole','Monger','Mongoose','Mongseng','Monk','Monkey','Moogle','Moon','Moonfolk','Mordenkainen','Mount','Mountain','Mouse','Mummy','Muraganda','Mutant',
    'Myr','Mystic','Nahiri','Narset','Nastiest,','Nautilus','Necron','Necros','Nephilim','New Earth','New Phyrexia','Nightmare','Nightstalker','Niko','Ninja','Nissa',
    'Nixilis','Noble','Noggle','Nomad','Nymph','Octopus','Ogre','Oko','Omen','Omenpath','Ooze','Orc','Orgg','Otter','Ouphe',"Outside Mutter's Spiral",
    'Ox','Oyster','Pangolin','Paratrooper','Peasant','Pegasus','Penguin','Performer','Pest','Phelddagrif','Phoenix','Phyrexia','Phyrexian','Pilot','Pirate','Plains',
    'Plant','Point','Pony','Porcupine','Possum','Power-Plant','Powerstone','Praetor','Primarch','Processor','Proper','Pyrulea','Qu','Quest','Quintorius','Rabbit',
    'Rabiah','Raccoon','Ral','Ranger','Rat','Rath','Ravnica','Realm','Rebel','Reflection','Regatha','Rhino','Rigger','Robot','Rogue','Room',
    'Rowan','Rune','Sable','Saga','Saheeli','Salamander','Samurai','Samut','Saproling','Sarkhan','Satyr','Scarecrow','Scientist','Scorpion','Scout','Seal',
    'Secret','Secret Lair','Segovia','Serpent','Serra','Serra’s Realm','Shade','Shadowmoor','Shaman','Shandalar','Shapeshifter','Shark','Sheep','Shenmeng','Ship','Shrine',
    'Siege','Siren','Sivitri','Skaro','Skeleton','Skunk','Slith','Sliver','Sloth','Slug','Snail','Snake','Soldier','Soltari','Sorin','Spacecraft',
    'Spawn','Specter','Spellshaper','Sphere','Sphinx','Spider','Spike','Spirit','Splinter','Sponge','Spuzzem','Spy','Squid','Squirrel','Starfish','Surrakar',
    'Survivor','Svega','Swamp','Symbiote','Synth','Szat','Tamiyo','Tarkir','Tasha','Teferi','Teyo','Tezzeret','Thalakos','The','The Abyss','The Dalek Asylum','The Library','Theros',
    'Thopter','Thrull','Thunder Junction','Tibalt','Tiefling','Time','Time Lord','Tower','Town','Townsfolk','Toy','Trap','Treasure','Tree','Treefolk','Trenzalore',
    'Trilobite','Troll','Turtle','Tyranid','Tyvar','Ugin',"Ulamog's",'Ulgrotha','Unicorn','Universia Beyondia','Unknown Planet','Urza',"Urza's",'Valla','Vampire','Vampyre',
    'Varmint','Vedalken','Vehicle','Venser','Villain','Vivien','Volver','Vraska','Vronos','Vryn','Waiter','Wall','Walrus','Wanderer','Warlock','Warrior',
    'Weasel','Weird','Werewolf','Whale','Wildfire','Will','Windgrace','Wizard','Wolf','Wolverine','Wombat','Worm','Wraith','Wrenn','Wrestler','Wurm',
    'Xenagos','Xerex','Yanggu','Yanling','Yeti','You','Zariel','Zendikar','Zhalfir','Zombie','Zonian','Zubera',
    'and/or','of','sECreT', 
]


COLORIDENTITY_DICT = {'Black': 'B', 'Green': 'G', 'Red': 'R', 'Blue': 'U', 'White': 'W'}
COLORIDENTITY_DICT_REVERSE = {v:k for k,v in COLORIDENTITY_DICT.items()}

LAYOUT = ['adventure', 'aftermath', 'augment', 'case', 'class', 'flip', 'host', 'leveler', 'meld', 'modal_dfc', 'mutate', 'normal', 'planar', 'prototype', 'reversible_card', 'saga', 'scheme', 'split', 'transform', 'vanguard']