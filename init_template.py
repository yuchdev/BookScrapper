# -*- coding: utf-8 -*-
import argparse
import fileinput
import subprocess
from datetime import date

DEFAULT_AUTHOR = "Yurii Cherkasov"
DEFAULT_EMAIL = "strategarius@protonmail.com"


def replace_in_file(file_path, old_text, new_text):
    """
    Replace single line in file
    """
    with fileinput.FileInput(file_path, inplace=True, backup='.bak') as file:
        for line in file:
            print(line.replace(old_text, new_text), end='')


def replace_content_file(file_path, new_content):
    """
    Replace entire file with new content
    """
    with open(file_path, 'w') as file:
        file.write(new_content)


def replace_template_name(template_name, new_module_name, new_description, author):
    """
    Replace template name with new module name in all files
    """
    capitalized_name = capitalize_name(new_module_name)
    print(f"Replace name to {new_module_name} in all files")
    print(f'User-friendly name: {capitalized_name}')

    # Replace in setup.cfg
    old_text = f'name = {template_name}'
    new_text = f'name = {new_module_name}'
    replace_in_file('setup.cfg', old_text=old_text, new_text=new_text)
    print(f"Replace '{old_text}' with '{new_text}' in setup.cfg")

    # Replace in README.md
    new_content = f'# {capitalized_name}\n\n{new_description}\n\n'
    replace_content_file('README.md', new_content)
    # Can't use f-string with //n
    print("Replace README.md content with '{}'".format(new_content.replace('\n', '\\n')))

    # Replace copyright in LICENSE
    current_year = date.today().year
    old_text = f'Copyright (c) 20xx {author}'
    new_text = f'Copyright (c) {current_year} {author}'
    replace_in_file('LICENSE', old_text=old_text, new_text=new_text)
    print(f"Replace '{old_text}' with '{new_text}' in LICENSE")

    # Replace in setup.py description
    old_text = '    description=None,'
    new_text = f'    description="{new_description}",'
    replace_in_file('setup.py', old_text=old_text, new_text=new_text)

    # Git move src/python_module to src/new_module_name
    subprocess.run(['git', 'mv', f'src/{template_name}', f'src/{new_module_name}'])

    # Git move test/bookscraper_test.py to test/new_module_name_test.py
    subprocess.run(['git', 'mv', f'test/{template_name}_test.py', f'test/{new_module_name}_test.py'])

    # In renamed file test/new_module_name_test.py
    old_text = 'class PythonModuleTest(unittest.TestCase):'
    new_text = f'class {capitalize_name(new_module_name)}Test(unittest.TestCase):'
    replace_in_file(f'test/{new_module_name}_test.py', old_text, new_text)
    print(f"Replace '{old_text}' with '{new_text}' in test/{new_module_name}_test.py")


def capitalize_name(name):
    # Capitalize each word in the name
    return ' '.join(word.capitalize() for word in name.split('_'))


def main():
    """
    :return: system exit code
    """
    parser = argparse.ArgumentParser(description='Update GitHub Python module template')
    parser.add_argument('new_module_name', help='New name for the Python module (with underscores)')
    parser.add_argument('--module-description', help='New description for the Python module', default='')
    parser.add_argument('--author-name', help='New author name', default=DEFAULT_AUTHOR)
    parser.add_argument('--author-email', help='New author email', default=DEFAULT_EMAIL)
    args = parser.parse_args()

    template_name = 'python_module'

    # Replace with the actual template name
    replace_template_name(template_name=template_name,
                          new_module_name=args.new_module_name,
                          new_description=args.module_description,
                          author=args.author_name)

    # Git commit
    subprocess.run(['git', 'commit', '--all', '--message',
                    f'Initialize template with name {args.new_module_name} and description "{args.module_description}"'])
    return 0


if __name__ == '__main__':
    main()
