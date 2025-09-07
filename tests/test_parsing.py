"""
Tests for the enhanced parsing functionality.

Tests all parsing scenarios including complex references,
discontinuous ranges, and cross-chapter references.
"""

import pytest
import sys
import os

# Add the parent directory to the path so we can import parsing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsing.reference_parser import ReferenceParser
from parsing.book_normalizer import BookNormalizer

class TestBookNormalizer:
    """Test book name normalization."""
    
    def test_normalize_psalm(self):
        normalizer = BookNormalizer()
        assert normalizer.normalize("Psalm") == "Psalms"
        assert normalizer.normalize("Ps") == "Psalms"
        assert normalizer.normalize("PSALM") == "Psalms"
        assert normalizer.normalize("PSALMS") == "Psalms"
    
    def test_normalize_unknown_book(self):
        normalizer = BookNormalizer()
        assert normalizer.normalize("John") == "John"
        assert normalizer.normalize("Matthew") == "Matthew"
    
    def test_add_custom_mapping(self):
        normalizer = BookNormalizer()
        normalizer.add_mapping("Mt", "Matthew")
        assert normalizer.normalize("Mt") == "Matthew"


class TestReferenceParser:
    """Test the main reference parser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock the parser to avoid actual API calls during testing
        self.parser = ReferenceParser(base_url="http://localhost:8081", version="asv")
        
        # Mock the _get_chapter_data method
        self.parser._get_chapter_data = self._mock_get_chapter_data
    
    def _mock_get_chapter_data(self, book, chapter, version):
        """Mock chapter data for testing."""
        # Return mock data for testing
        return {
            "verses": {
                "1": "The word that came to Jeremiah from the Lord:",
                "2": "Arise and go down to the potter's house, and there I will let you hear my words.",
                "3": "So I went down to the potter's house, and there he was working at his wheel.",
                "4": "The vessel he was making of clay was spoiled in the potter's hand, and he reworked it into another vessel, as seemed good to him.",
                "5": "Then the word of the Lord came to me:",
                "6": "Can I not do with you, O house of Israel, just as this potter has done? says the Lord. Just like the clay in the potter's hand, so are you in my hand, O house of Israel.",
                "7": "At one moment I may declare concerning a nation or a kingdom, that I will pluck up and break down and destroy it,",
                "8": "but if that nation, concerning which I have spoken, turns from its evil, I will change my mind about the disaster that I intended to bring on it.",
                "9": "And at another moment I may declare concerning a nation or a kingdom that I will build and plant it,",
                "10": "but if it does evil in my sight, not listening to my voice, then I will change my mind about the good that I had intended to do to it.",
                "11": "Now, therefore, say to the people of Judah and the inhabitants of Jerusalem: Thus says the Lord: Look, I am a potter shaping evil against you and devising a plan against you. Turn now, all of you from your evil way, and amend your ways and your doings."
            }
        }
    
    def test_parse_simple_reference(self):
        """Test parsing simple references like 'Jeremiah 18:1-11'."""
        result = self.parser.parse("Jeremiah 18:1-11", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Jeremiah 18:1-11"
        assert result["book"] == "Jeremiah"
        assert result["chapter"] == "18"
        assert len(result["verses"]) == 11
        assert result["formatted_text"]  # Just check that we have formatted text
    
    def test_parse_single_verse(self):
        """Test parsing single verses like 'Jeremiah 18:5'."""
        result = self.parser.parse("Jeremiah 18:5", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Jeremiah 18:5"
        assert len(result["verses"]) == 1
        assert result["verses"][0]["verse"] == "5"
    
    def test_parse_discontinuous_range(self):
        """Test parsing discontinuous ranges like 'Psalm 139:1-5, 12-17'."""
        # Mock Psalms data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "1": "O Lord, you have searched me and known me.",
                "2": "You know when I sit down and when I rise up; you discern my thoughts from far away.",
                "3": "You search out my path and my lying down, and are acquainted with all my ways.",
                "4": "Even before a word is on my tongue, O Lord, you know it completely.",
                "5": "You hem me in, behind and before, and lay your hand upon me.",
                "12": "Even the darkness is not dark to you; the night is as bright as the day, for darkness is as light to you.",
                "13": "For it was you who formed my inward parts; you knit me together in my mother's womb.",
                "14": "I praise you, for I am fearfully and wonderfully made. Wonderful are your works; that I know very well.",
                "15": "My frame was not hidden from you, when I was being made in secret, intricately woven in the depths of the earth.",
                "16": "Your eyes beheld my unformed substance. In your book were written all the days that were formed for me, when none of them as yet existed.",
                "17": "How weighty to me are your thoughts, O God! How vast is the sum of them!"
            }
        }
        
        result = self.parser.parse("Psalm 139:1-5, 12-17", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Psalm 139:1-5, 12-17"
        assert result["book"] == "Psalms"  # Should be normalized
        assert len(result["verses"]) == 11  # 5 + 6 verses
        assert result["formatted_text"]  # Just check that we have formatted text
    
    def test_parse_cross_chapter_reference(self):
        """Test parsing cross-chapter references like 'John 3:16-4:1'."""
        # Mock John data for chapters 3 and 4
        def mock_get_chapter_data(book, chapter, version):
            if chapter == "3":
                return {
                    "verses": {
                        "16": "For God so loved the world that he gave his only Son, so that everyone who believes in him may not perish but may have eternal life.",
                        "17": "Indeed, God did not send the Son into the world to condemn the world, but in order that the world might be saved through him.",
                        "18": "Those who believe in him are not condemned; but those who do not believe are condemned already, because they have not believed in the name of the only Son of God.",
                        "19": "And this is the judgment, that the light has come into the world, and people loved darkness rather than light because their deeds were evil.",
                        "20": "For all who do evil hate the light and do not come to the light, so that their deeds may not be exposed.",
                        "21": "But those who do what is true come to the light, so that it may be clearly seen that their deeds have been done in God."
                    }
                }
            elif chapter == "4":
                return {
                    "verses": {
                        "1": "Now when Jesus learned that the Pharisees had heard that Jesus was making and baptizing more disciples than John"
                    }
                }
            return None
        
        self.parser._get_chapter_data = mock_get_chapter_data
        
        result = self.parser.parse("John 3:16-4:1", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "John 3:16-4:1"
        assert result["book"] == "John"
        assert result["start_chapter"] == 3
        assert result["end_chapter"] == 4
        assert len(result["verses"]) == 7  # 6 from ch 3 + 1 from ch 4
    
    def test_parse_verse_with_suffix(self):
        """Test parsing verses with suffixes like 'Habakkuk 3:2-19a'."""
        # Mock Habakkuk data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "2": "O Lord, I have heard of your renown, and I stand in awe, O Lord, of your work. In our own time revive it; in our own time make it known; in wrath may you remember mercy.",
                "3": "God came from Teman, the Holy One from Mount Paran. Selah. His glory covered the heavens, and the earth was full of his praise.",
                "4": "His brightness was like the sun, and rays came forth from his hand, where his power lay hidden.",
                "5": "Before him went pestilence, and plague followed close behind.",
                "6": "He stopped and shook the earth; he looked and made the nations tremble. The eternal mountains were shattered; along his ancient pathways the everlasting hills sank low.",
                "7": "I saw the tents of Cushan in affliction; the tent-curtains of the land of Midian trembled.",
                "8": "Was your wrath against the rivers, O Lord? Was your anger against the rivers, or your indignation against the sea, when you rode on your horses, on your chariots of salvation?",
                "9": "You stripped the sheath from your bow, and put the arrows to the string. Selah. You split the earth with rivers.",
                "10": "The mountains saw you, and writhed; a torrent of water swept by; the deep gave forth its voice. The sun raised high its hands;",
                "11": "the moon stood still in its exalted place, at the light of your arrows speeding by, at the gleam of your flashing spear.",
                "12": "In fury you trod the earth, in anger you trampled nations.",
                "13": "You went forth for the salvation of your people, for the salvation of your anointed. You crushed the head of the wicked house, laying it bare from foundation to roof. Selah.",
                "14": "You pierced with his own arrows the head of his warriors, who came like a whirlwind to scatter us, gloating as if ready to devour the poor who were in hiding.",
                "15": "You trampled the sea with your horses, churning the mighty waters.",
                "16": "I hear, and I tremble within; my lips quiver at the sound. Rottenness enters into my bones, and my steps tremble beneath me. I wait quietly for the day of calamity to come upon the people who attack us.",
                "17": "Though the fig tree does not blossom, and no fruit is on the vines; though the produce of the olive fails, and the fields yield no food; though the flock is cut off from the fold, and there is no herd in the stalls,",
                "18": "yet I will rejoice in the Lord; I will exult in the God of my salvation.",
                "19": "God, the Lord, is my strength; he makes my feet like the feet of a deer, and makes me tread upon the heights. To the choirmaster: with stringed instruments."
            }
        }
        
        result = self.parser.parse("Habakkuk 3:2-19a", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Habakkuk 3:2-19a"
        assert len(result["verses"]) == 18  # 2 through 19
        assert result["formatted_text"]  # Just check that we have formatted text
    
    def test_parse_end_reference(self):
        """Test parsing references with 'end' like 'Jeremiah 18:5-end'."""
        result = self.parser.parse("Jeremiah 18:5-end", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Jeremiah 18:5-end"
        assert len(result["verses"]) == 7  # 5 through 11
        assert result["formatted_text"]  # Just check that we have formatted text
    
    def test_parse_invalid_reference(self):
        """Test parsing invalid references."""
        result = self.parser.parse("", "asv")
        
        assert result["parsed"] == False
        assert "Empty reference" in result["error"]
        assert result["formatted_text"] == "[Reading: ]"
    
    def test_parse_nonexistent_book(self):
        """Test parsing references with non-existent books."""
        # Mock empty response for non-existent book
        self.parser._get_chapter_data = lambda book, chapter, version: None
        
        result = self.parser.parse("Nonexistent 1:1", "asv")
        
        assert result["parsed"] == False
        assert "Could not fetch chapter data" in result["error"]
        assert result["formatted_text"] == "[Reading: Nonexistent 1:1]"
    
    def test_parse_chapter_only_reference(self):
        """Test parsing chapter-only references like 'Philemon 1-21'."""
        # Mock Philemon data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "1": "Paul, a prisoner of Christ Jesus, and Timothy our brother, To Philemon our dear friend and fellow worker,",
                "2": "and to Apphia our sister and Archippus our fellow soldier—and to the church that meets in your home:",
                "3": "Grace and peace to you from God our Father and the Lord Jesus Christ.",
                "4": "I always thank my God as I remember you in my prayers,",
                "5": "because I hear about your love for all his holy people and your faith in the Lord Jesus.",
                "6": "I pray that your partnership with us in the faith may be effective in deepening your understanding of every good thing we share for the sake of Christ.",
                "7": "Your love has given me great joy and encouragement, because you, brother, have refreshed the hearts of the Lord's people.",
                "8": "Therefore, although in Christ I could be bold and order you to do what you ought to do,",
                "9": "yet I prefer to appeal to you on the basis of love. It is as none other than Paul—an old man and now also a prisoner of Christ Jesus—",
                "10": "that I appeal to you for my son Onesimus, who became my son while I was in chains.",
                "11": "Formerly he was useless to you, but now he has become useful both to you and to me.",
                "12": "I am sending him—who is my very heart—back to you.",
                "13": "I would have liked to keep him with me so that he could take your place in helping me while I am in chains for the gospel.",
                "14": "But I did not want to do anything without your consent, so that any favor you do would not seem forced but would be voluntary.",
                "15": "Perhaps the reason he was separated from you for a little while was that you might have him back forever—",
                "16": "no longer as a slave, but better than a slave, as a dear brother. He is very dear to me but even dearer to you, both as a fellow man and as a brother in the Lord.",
                "17": "So if you consider me a partner, welcome him as you would welcome me.",
                "18": "If he has done you any wrong or owes you anything, charge it to me.",
                "19": "I, Paul, am writing this with my own hand. I will pay it back—not to mention that you owe me your very self.",
                "20": "I do wish, brother, that I may have some benefit from you in the Lord; refresh my heart in Christ.",
                "21": "Confident of your obedience, I write to you, knowing that you will do even more than I ask."
            }
        }
        
        result = self.parser.parse("Philemon 1-21", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Philemon 1-21"
        assert result["book"] == "Philemon"
        assert result["chapter"] == "1"
        assert len(result["verses"]) == 21  # All verses from 1 to 21
    
    def test_parse_psalm_without_verses(self):
        """Test parsing Psalm references without verses like 'Psalm 146'."""
        # Mock Psalm 146 data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "1": "Praise the Lord. Praise the Lord, my soul.",
                "2": "I will praise the Lord all my life; I will sing praise to my God as long as I live.",
                "3": "Do not put your trust in princes, in human beings, who cannot save.",
                "4": "When their spirit departs, they return to the ground; on that very day their plans come to nothing.",
                "5": "Blessed are those whose help is the God of Jacob, whose hope is in the Lord their God.",
                "6": "He is the Maker of heaven and earth, the sea, and everything in them— he remains faithful forever.",
                "7": "He upholds the cause of the oppressed and gives food to the hungry. The Lord sets prisoners free,",
                "8": "the Lord gives sight to the blind, the Lord lifts up those who are bowed down, the Lord loves the righteous.",
                "9": "The Lord watches over the foreigner and sustains the fatherless and the widow, but he frustrates the ways of the wicked.",
                "10": "The Lord reigns forever, your God, O Zion, for all generations. Praise the Lord."
            }
        }
        
        result = self.parser.parse("Psalm 146", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Psalm 146"
        assert result["book"] == "Psalms"  # Should be normalized
        assert result["chapter"] == "146"
        assert len(result["verses"]) == 10  # All verses in the chapter
    
    def test_parse_optional_verses(self):
        """Test parsing optional verses like 'Luke 1:39-45[46-55]'."""
        # Mock Luke 1 data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "39": "At that time Mary got ready and hurried to a town in the hill country of Judea,",
                "40": "where she entered Zechariah's home and greeted Elizabeth.",
                "41": "When Elizabeth heard Mary's greeting, the baby leaped in her womb, and Elizabeth was filled with the Holy Spirit.",
                "42": "In a loud voice she exclaimed: 'Blessed are you among women, and blessed is the child you will bear!'",
                "43": "But why am I so favored, that the mother of my Lord should come to me?",
                "44": "As soon as the sound of your greeting reached my ears, the baby in my womb leaped for joy.",
                "45": "Blessed is she who has believed that the Lord would fulfill his promises to her!'",
                "46": "And Mary said: 'My soul glorifies the Lord",
                "47": "and my spirit rejoices in God my Savior,",
                "48": "for he has been mindful of the humble state of his servant. From now on all generations will call me blessed,",
                "49": "for the Mighty One has done great things for me— holy is his name.",
                "50": "His mercy extends to those who fear him, from generation to generation.",
                "51": "He has performed mighty deeds with his arm; he has scattered those who are proud in their inmost thoughts.",
                "52": "He has brought down rulers from their thrones but has lifted up the humble.",
                "53": "He has filled the hungry with good things but has sent the rich away empty.",
                "54": "He has helped his servant Israel, remembering to be merciful",
                "55": "to Abraham and his descendants forever, just as he promised our ancestors.'"
            }
        }
        
        result = self.parser.parse("Luke 1:39-45[46-55]", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Luke 1:39-45[46-55]"
        assert result["book"] == "Luke"
        assert result["chapter"] == "1"
        assert len(result["verses"]) == 7  # 39-45
        assert "optional_verses" in result  # Should have optional verses
        assert len(result["optional_verses"]) == 10  # 46-55
    
    def test_parse_discontinuous_range_with_single_verse(self):
        """Test parsing discontinuous ranges like 'Psalm 104:26-36,37'."""
        # Mock Psalm 104 data
        self.parser._get_chapter_data = lambda book, chapter, version: {
            "verses": {
                "26": "There the ships go to and fro, and Leviathan, which you formed to frolic there.",
                "27": "All creatures look to you to give them their food at the proper time.",
                "28": "When you give it to them, they gather it up; when you open your hand, they are satisfied with good things.",
                "29": "When you hide your face, they are terrified; when you take away their breath, they die and return to the dust.",
                "30": "When you send your Spirit, they are created, and you renew the face of the ground.",
                "31": "May the glory of the Lord endure forever; may the Lord rejoice in his works—",
                "32": "he who looks at the earth, and it trembles, who touches the mountains, and they smoke.",
                "33": "I will sing to the Lord all my life; I will sing praise to my God as long as I live.",
                "34": "May my meditation be pleasing to him, as I rejoice in the Lord.",
                "35": "But may sinners vanish from the earth and the wicked be no more. Praise the Lord, my soul. Praise the Lord.",
                "36": "Praise the Lord, my soul. Praise the Lord.",
                "37": "Praise the Lord, my soul. Praise the Lord."
            }
        }
        
        result = self.parser.parse("Psalm 104:26-36,37", "asv")
        
        assert result["parsed"] == True
        assert result["reference"] == "Psalm 104:26-36,37"
        assert result["book"] == "Psalms"  # Should be normalized
        assert result["chapter"] == "104"
        assert len(result["verses"]) == 12  # 26-36 (11 verses) + 37 (1 verse) = 12 total

if __name__ == "__main__":
    pytest.main([__file__])
