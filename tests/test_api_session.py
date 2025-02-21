# Todo:
# - Add Openai test f_header and general test_header

from init_tests import append_to_path

append_to_path()

import unittest

import api_session
import ui
from constants import * 

class TestSession(unittest.TestCase):
    def test_session_client_init(self):
        ''' Test if the attribute client.api matches the expected module. '''
        for client_alias, client_id in ALIAS_TO_CLIENT.items():
            with self.subTest(client_id=client_id):
                session = api_session.Session(client_id)
                
                module_str = str(session.client.api)
                
                # Remove source of import.
                # Example: <module 'x' from '/Library/...
                module_str = module_str.split(' from ')[0]

                if session.type == TYPE_TEST:
                    expected_module_str = 'None'
                elif session.type == TYPE_GEMINI:
                    expected_module_str = "<module 'google.generativeai'"
                elif session.type == TYPE_GOOGLE:
                    expected_module_str = "None"
                elif session.type == TYPE_OPENAI:
                    expected_module_str = "<module 'openai'"

                self.assertEqual(module_str, expected_module_str)

class _OpenaiAPIResponseMessageObject:
    def __init__(self, text):
        self.content = text

class _OpenaiAPIResponseChoiceObject:
    def __init__(self, text):
        self.message = _OpenaiAPIResponseMessageObject(text)
        self.delta = _OpenaiAPIResponseMessageObject(text)

class _OpenaiAPIResponseObject:
    ''' Doubles as a 'chunk' object. '''
    def __init__(self, text=''):
        choice_object = _OpenaiAPIResponseChoiceObject(text)

        self.choices = [choice_object]

        self.chunks = []
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.chunks:
            return self.chunks.pop(0)
        else:
            raise StopIteration
        
    def create_chunks(self, text):
        split_text = text.split('\n')
        
        for part in split_text:
            part += '\n'
            chunk = _OpenaiAPIResponseObject(part)

            self.chunks.append(chunk)

class TestOpenaiClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = api_session.Session(GPT_4O_MINI_ID)
        cls.client = cls.session.client 

    @classmethod
    def tearDownClass(cls):
        del cls.session

    def setUp(self):
        self.session.reset()
        self.client.sys_message = None
        self.client.previous_sys_message = None
        self.client.context = []

    def tearDown(self):
        pass

    def test_header(self):
        pre = '### Methods to Scroll Half a Page in VS Code:\nText'
        expected =  '\033[39;49;1m-- Methods to Scroll Half a Page in VS Code:\033[22m\nText'
        post = self.client.f_header(pre)
        self.assertEqual(post, expected)

    def _create_message_and_compare(self, role, text, expected):
        message = self.client.create_message(role, text)
        self.assertIsInstance(message, dict)
        self.assertEqual(message, expected)

    def test_create_message_single_line(self):
        role = "user"
        text = "I am dog."
        expected = {"role": "user", "content": "I am dog."}
        self._create_message_and_compare(role, text, expected)

    def test_update_sys_message_context(self):
        context = self.client.context
        client = self.client

        sys_message = "First System Message"
        message = "First Message"

        client.sys_message = sys_message
        client.update_context(message)
        expected = [sys_message, message]

        self.assertEqual(context, expected)
        self.assertEqual(client.current_sys_message, "First System Message")

        client.sys_message = sys_message
        message = "Second Message"
        client.update_context(message)
        expected.append(message)

        self.assertEqual(context, expected)
        self.assertEqual(client.current_sys_message, "First System Message")

        sys_message = "Second System Message"
        message = "Third Message"

        client.sys_message = sys_message
        client.update_context(message)
        expected.append(sys_message)
        expected.append(message)

        self.assertEqual(context, expected)
        self.assertEqual(client.current_sys_message, "Second System Message")

        sys_message = "Third System Message"
        message = "Fourth Message"

        client.sys_message = sys_message
        client.update_context(message)
        expected.append(sys_message)
        expected.append(message)

        self.assertEqual(context, expected)
        self.assertEqual(client.current_sys_message, "Third System Message")

    def test_update_context(self):
        context = self.client.context
        client = self.client

        messages = ["first", "second", "third", "fourth"]

        expected = []

        for message in messages:
            client.set_query(f"{message} query")
            expected.append({"role": "user", "content": f"{message} query"})
            self.assertEqual(context, expected)

            client.api_response = _OpenaiAPIResponseObject(f"{message} response")
            client.format_response()
            expected.append({"role": "assistant", "content": f"{message} response"})
            self.assertEqual(context, expected)

    def test_update_context_streaming(self):
        context = self.client.context
        client = self.client

        client.api_response = _OpenaiAPIResponseObject()
        
        full_text = "This is line 1\nThis is line 2\nThis is line 3"
        client.api_response.create_chunks(full_text)

        client.output_stream(format=True)

        full_text += '\n'
        expected = [client.create_message("assistant", full_text)]
        self.assertEqual(context, expected)

class TestFormatResponse(unittest.TestCase):

    texts = {   "code_block_containing_boldened_text": "```python\n**boldened**\n```**boldened**",
                "code_block_multiple": "```python\nCode\n```\nText\n```C++\nCode\n```\nText",
                "code_block_containing_italicized_text": "```python\nHey, some *code*\n```",
                "inline_code_single": "text`**not bold**` text",
                "inline_code_multiple": "text`**not bold**` text `*not italic*`",
                "inline_code_multi_line_single": "text `text \n**bold**`",
                "inline_code_multi_line_multiple": "text `code \n**bold**`\n`**notbold**`",
                "bullet_list_multi_line": '''
* 1 cup red lentils, rinsed
* 2 cups water or vegetable broth
* 1 tbsp oil
* 1 tsp ground cumin
* 1 tsp ground coriander
* ½ tsp turmeric powder
* ½ tsp garam masala
* ¼ tsp cayenne pepper (optional)
* 1 small onion, chopped
* 2 cloves garlic, minced
* 1 inch ginger, grated
* Salt to taste
* Fresh cilantro, chopped (for garnish)''', 
                "bullet_list_multi_line_indented": '''1. Test CMake Directly:
   * Install CMake independently of Homebrew (e.g., from the CMake website's official macOS distribution).  
   * Create a simple CMake project (e.g., `CMakeLists.txt` containing `cmake_minimum_required(VERSION 3.10) project(MyProject) add_executable(MyProject main.cpp)`, and `main.cpp` containing a basic "Hello, world!" program).
   * Try to build it using the independently installed CMake from the command line. This helps determine if CMake itself is malfunctioning.''',
                "bullet_item": "\n* Large pot or Dutch oven",
                "bullet_item_boldened_text_normal_text": "\n* **Boldened Text** Unboldened text.",
                "bullet_item_boldened_italic_text": "\n* ***Boldened Italic.***",
                "bullet_item_boldened_text_asterisks": "\n* * **Boldened NOT Italic.** *",
                "bullet_item_indented": "\n    * A",
                "bullet_item_asterisk": "\n* Dial *555",
                "italic_text_containing_boldened_text": "*Italic **bold-italic** Italic*",
                "boldened_italic_close": "***Hey***",
             }
    f_texts = { "code_block_containing_boldened_text": "\tpython: - - - - -\n**boldened**\n\t- - - - - - - - - -\033[39;49;1mboldened\033[22m",
                "code_block_multiple": "\tpython: - - - - -\nCode\n\t- - - - - - - - - -\nText\n\tC++: - - - - -\nCode\n\t- - - - - - - - - -\nText",
                "code_block_containing_italicized_text": "\tpython: - - - - -\nHey, some *code*\n\t- - - - - - - - - -",
                "inline_code_single": "text`**not bold**` text",
                "inline_code_multiple": "text`**not bold**` text `*not italic*`",
                "inline_code_multi_line_single": "text `text \n\033[39;49;1mbold\033[22m`",
                "inline_code_multi_line_multiple": "text `code \n\033[39;49;1mbold\033[22m`\n`**notbold**`",
                "bullet_list_multi_line": '''
- 1 cup red lentils, rinsed
- 2 cups water or vegetable broth
- 1 tbsp oil
- 1 tsp ground cumin
- 1 tsp ground coriander
- ½ tsp turmeric powder
- ½ tsp garam masala
- ¼ tsp cayenne pepper (optional)
- 1 small onion, chopped
- 2 cloves garlic, minced
- 1 inch ginger, grated
- Salt to taste
- Fresh cilantro, chopped (for garnish)''',
                "bullet_list_multi_line_indented": '''1. Test CMake Directly:
   - Install CMake independently of Homebrew (e.g., from the CMake website's official macOS distribution).  
   - Create a simple CMake project (e.g., `CMakeLists.txt` containing `cmake_minimum_required(VERSION 3.10) project(MyProject) add_executable(MyProject main.cpp)`, and `main.cpp` containing a basic "Hello, world!" program).
   - Try to build it using the independently installed CMake from the command line. This helps determine if CMake itself is malfunctioning.''',
                "bullet_item": "\n- Large pot or Dutch oven",
                "bullet_item_boldened_text_normal_text": "\n- \033[39;49;1mBoldened Text\033[22m Unboldened text.",
                "bullet_item_boldened_italic_text": "\n- \033[39;49;1m\033[39;49;3mBoldened Italic.\033[22m\033[23m",
                "bullet_item_boldened_text_asterisks": "\n- * \033[39;49;1mBoldened NOT Italic.\033[22m *",
                "bullet_item_indented": "\n    - A",
                "bullet_item_asterisk": "\n- Dial *555",
                "italic_text_containing_boldened_text": "\033[39;49;3mItalic \033[39;49;1mbold-italic\033[22m Italic\033[23m",
                "boldened_italic_close": "\033[39;49;1m\033[39;49;3mHey\033[22m\033[23m",
               }

    expected_failures = []

    def func(self, pre):
        ''' The function we are testing. Returns relevant modified variable '''
        self.format_response(text=pre)
        return self.session.client.response

    def compare(self, pre, expected, key): 
        ''' Assers equality if key is not in self.expected_failures else inequality. '''

        post = self.func(pre)

        if key in self.expected_failures:
            self.assertNotEqual(post, expected)
        else:
            self.assertEqual(post, expected)

    def test_format_response(self):
        clients = [GPT_4_ID, GEMINI_FLASH_ID] # One per type

        for client_id in clients:
            self.session = api_session.Session(client_id)
            self.format_response = self.session.client.format_response
            for key in self.texts:
               with self.subTest(client_id=client_id, key=key):
                    pre = self.texts[key]
                    expected = self.f_texts[key]

                    self.compare(pre, expected, key)
    
class TestGeminiFormatHelperFunctions(unittest.TestCase):
    ''' Tests the formatting methods used by GeminiClient.format_response(). '''

    # Specific to Gemini, insert new f_code_blocks() function.   
    # "code_block_containing_numbered_list_item": "```python\n**1. Item\n```\n**2.",
    # "code_block_containing_numbered_list_item": "\tpython: - - - - -\n**1. Item\n\t- - - - - - - - - -\n2.",

    texts = {
        "bullet-complex": "* **Text",
        "bullet-streamed": "*\nText",
        "bullet-multiline": "* Text\n* Text",
        "bullet-multiline-streamed": "*\nText\n*\nText",
        "bullet-indented-tab": "\t* Text",
        "bullet-indented-spaces": "\n    * Text",
        "numbered_lists-item": "**1.",
        "numbered_lists-list": "**1. Text\n**2. Text",
        "header-1": "\t# Header 1 #",
        "header-1-not": "\t # Header",
        "bold_text-simple": "**Text**",
        "bold_text-not": "** * Text ***",
        "simple_math-mult-A": "5 * 10 = 9",
        "simple_math-mult-B": "5*10 = 9",
        "simple_math-mult-B": "5*10 * 3 = 9",
        "simple_math-mult-C": "5*10*3 = 9",
        "italicized_text-one-char": "The number *e*, approximately",
        "italicized_text-asterisks": " *** ",
        "italicized_text-sentence-with-asterisks": "Hey * this is not * italicized",
        "italicized_text-sentence-with-asterisks-B": "Hey *this is not * italicized",
        "italicized_text-sentence": "Hey *this is* italicized",
        "italicized_text-sentence-with-asterisk": "Hey *this is* also* italicized",
        "italicized_text-asterisk-inside-word": "'*args' text '*args'.",
        "italicized_text-italicized-asterisk-inside-word": "**args* text '*args'.",
        "italicized_text-asterisk-in-word-sentence": "`*args`: The `*args` syntax in your `calculate` function definition means *it can accept a variable number of positional arguments*.  These arguments are packed into a tuple named `*args` inside the function."
        }
    f_texts = {
        "bullet-complex": "- Text",
        "bullet-streamed": "- Text",
        "bullet-multiline": "- Text\n- Text",
        "bullet-multiline-streamed": "- Text\n- Text",
        "bullet-indented-spaces": "\n    - Text",
        "bullet-indented-tab": "\t- Text",
        "numbered_lists-item": "1.",
        "numbered_lists-list": "1. Text\n2. Text",
        "header-1": "\t\t Header 1 #",
        "header-1-not": "\t # Header",
        "bold_text-simple": "\033[39;49;1mText\033[22m",
        "bold_text-not": "\033[39;49;1m * Text *\033[22m",
        "simple_math-mult-A": "5 * 10 = 9",
        "simple_math-mult-B": "5*10 = 9",
        "simple_math-mult-B": "5*10 * 3 = 9",
        "simple_math-mult-C": "5*10*3 = 9",
        "italicized_text-one-char": "The number \033[39;49;3me\033[23m, approximately",
        "italicized_text-asterisks": " *** ",
        "italicized_text-sentence-with-asterisks": "Hey * this is not * italicized",
        "italicized_text-sentence-with-asterisks-B": "Hey *this is not * italicized",
        "italicized_text-sentence": "Hey \033[39;49;3mthis is\033[23m italicized",
        "italicized_text-sentence-with-asterisk": "Hey \033[39;49;3mthis is\033[23m also* italicized",
        "italicized_text-asterisk-inside-word": "'*args' text '*args'.",
        "italicized_text-italicized-asterisk-inside-word": "*\033[39;49;3margs\033[23m text '*args'.",
        "italicized_text-asterisk-in-word-sentence": "`*args`: The `*args` syntax in your `calculate` function definition means \033[39;49;3mit can accept a variable number of positional arguments\033[23m.  These arguments are packed into a tuple named `*args` inside the function."
        }

    expected_failures = [
        ["f_bold_text", "bold_text-not"],
        ["f_italicized_text", "bold_text-simple"],
        ]

    @classmethod
    def setUpClass(cls):
        cls.session = api_session.Session(GEMINI_FLASH_ID)
        cls.format_response = cls.session.client.format_response

    @classmethod
    def tearDownClass(cls):
        del cls.session

    def run_tests(self, function_name):
        func = getattr(self.session.client, function_name)

        for key in self.texts:
            with self.subTest(key=key):
                expected = self.get_expected(function_name, key)
                pre = self.texts[key]

                post = func(pre)

                pair = [function_name, key]
                
                if pair in self.expected_failures:
                    self.assertNotEqual(post, expected)
                else:
                    self.assertEqual(post, expected)

    def get_expected(self, function_name, current):
        ''' Returns expected output for each function name. '''

        function_name = function_name.strip('f_')

        if current.startswith(function_name):
            return self.f_texts[current]
        else:
            return self.texts[current]

    def test_f_bullet(self):
        function_name = 'f_bullet'

        self.run_tests(function_name)

    def test_f_numbered_lists(self):
        function_name = 'f_numbered_lists'

        self.run_tests(function_name)

    def test_f_header(self):
        function_name = 'f_header'

        self.run_tests(function_name)

    def test_f_bold_text(self):
        function_name = 'f_bold_text'

        self.run_tests(function_name)
    
    def test_f_italicized_text(self):
        function_name = 'f_italicized_text'
        
        self.run_tests(function_name)

class TestOpenaiFormatHelperFunctions(unittest.TestCase):
    texts = {
        'bullet-streamed': '*\nText',
        'bullet-multiline': '* Text\n* Text',
        'bullet-multiline-streamed': '*\nText\n*\nText',
        'bullet-indented-tab': '\t* Text',
        'bullet-indented-spaces': '\n    * Text',
        'bold_text-simple': '**Text**',
        'bold_text-not': '** * Text ***',
        'simple_math-mult-A': '5 * 10 = 9',
        'simple_math-mult-B': '5*10 = 9',
        'simple_math-mult-B': '5*10 * 3 = 9',
        'simple_math-mult-C': '5*10*3 = 9',
        'italicized_text-one-char': 'The number *e*, approximately',
        'italicized_text-asterisks': ' *** ',
        'italicized_text-sentence-with-asterisks': 'Hey * this is not * italicized',
        'italicized_text-sentence-with-asterisks-B': 'Hey *this is not * italicized',
        'italicized_text-sentence': 'Hey *this is* italicized',
        'italicized_text-sentence-with-asterisk': 'Hey *this is* also* italicized',
        'italicized_text-asterisk-inside-word': "'*args' text '*args'.",
        'italicized_text-italicized-asterisk-inside-word': "**args* text '*args'.",
        'italicized_text-asterisk-in-word-sentence': "`*args`: The `*args` syntax in your `calculate` function definition means *it can accept a variable number of positional arguments*.  These arguments are packed into a tuple named `*args` inside the function."
        }
    f_texts = {
        'bullet-streamed': '- Text',
        'bullet-multiline': '- Text\n- Text',
        'bullet-multiline-streamed': '- Text\n- Text',
        'bullet-indented-spaces': '\n    - Text',
        'bullet-indented-tab': '\t- Text',
        'bold_text-simple': '\033[39;49;1mText\033[22m',
        'bold_text-not': '\033[39;49;1m * Text *\033[22m',
        'simple_math-mult-A': '5 * 10 = 9',
        'simple_math-mult-B': '5*10 = 9',
        'simple_math-mult-B': '5*10 * 3 = 9',
        'simple_math-mult-C': '5*10*3 = 9',
        'italicized_text-one-char': 'The number \033[39;49;3me\033[23m, approximately',
        'italicized_text-asterisks': ' *** ',
        'italicized_text-sentence-with-asterisks': 'Hey * this is not * italicized',
        'italicized_text-sentence-with-asterisks-B': 'Hey *this is not * italicized',
        'italicized_text-sentence': 'Hey \033[39;49;3mthis is\033[23m italicized',
        'italicized_text-sentence-with-asterisk': 'Hey \033[39;49;3mthis is\033[23m also* italicized',
        'italicized_text-asterisk-inside-word': "'*args' text '*args'.",
        'italicized_text-italicized-asterisk-inside-word': "*\033[39;49;3margs\033[23m text '*args'.",
        'italicized_text-asterisk-in-word-sentence': "`*args`: The `*args` syntax in your `calculate` function definition means \033[39;49;3mit can accept a variable number of positional arguments\033[23m.  These arguments are packed into a tuple named `*args` inside the function."
        }

    expected_failures = [
        ['f_bold_text', 'bold_text-not'],
        ['f_italicized_text', 'bold_text-simple']
    ]

    @classmethod
    def setUpClass(cls):
        cls.session = api_session.Session(GPT_4_ID)
        cls.format_response = cls.session.client.format_response

    @classmethod
    def tearDownClass(cls):
        del cls.session

    def run_tests(self, function_name):
        func = getattr(self.session.client, function_name)

        for key in self.texts:
            with self.subTest(key=key):
                expected = self.get_expected(function_name, key)
                pre = self.texts[key]

                post = func(pre)

                pair = [function_name, key]
                
                if pair in self.expected_failures:
                    self.assertNotEqual(post, expected)
                else:
                    self.assertEqual(post, expected)

    def get_expected(self, function_name, current):
        ''' Returns expected output for each function name. '''

        function_name = function_name.strip('f_')

        if current.startswith(function_name):
            return self.f_texts[current]
        else:
            return self.texts[current]

    def test_f_bullet(self):
        function_name = 'f_bullet'

        self.run_tests(function_name)

    def test_f_bold_text(self):
        function_name = 'f_bold_text'

        self.run_tests(function_name)
    
    def test_f_italicized_text(self):
        function_name = 'f_italicized_text'
        
        self.run_tests(function_name)

if __name__ == '__main__':
    unittest.main(verbosity=2)