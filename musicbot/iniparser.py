import os


def hard_write(of, content):
    """Creates necessary directories and writes file.

    :param of: Path to output file
    :type of: str
    :param content: Content to be written to file
    """
    os.makedirs(os.path.dirname(of), exist_ok=True)
    with open(of, "w") as f:
        f.write(content)


class IniParser:

    class PythonIni:

        def __init__(self, sections=[]):
            """
            :param sections: List of :class:`IniSection` objects.
            :type sections: list
            """
            if not isinstance(sections, list):
                raise TypeError((f"sections must be a list, not "
                                 f"{sections.__class__.__name__}"))
            self.sections = sections

        def to_dict(self, sectioned=True):
            """Returns this object converted to dictionary.

            :param sectioned: `True` if dict should be nested with
                inner dicts for each ini-section.
            :type sectioned: bool, optional
            """
            ini_dict = {}
            for sec in self.sections:
                if sectioned:
                    ini_dict[sec.name] = sec.values
                else:
                    for key_name in sec.values:
                        ini_dict[key_name] = sec.values[key_name]
            return ini_dict

        def __getitem__(self, section_name):
            for sec in self.sections:
                if sec.name == section_name:
                    return sec
            raise KeyError

        def rename(self, old, new):
            """Renames a section or key. Useful for shortening names
            for repeated use within your script. To rename a section,
            include brackets ([SECTION]) in the parameters.

            :param old: Old (current) name of section/key
            :type old: str
            :param new: New name of section/key
            :type new: str
            """
            if "[" in new and "]" in old:   # Rename section
                for sec in self.sections:
                    if old.strip("[]") == sec.name:
                        sec.name = new.strip("[]")
                        return
            for sec in self.sections:
                for key in sec.values:
                    if key == old:
                        sec.values[new] = sec.values.pop(key)
                        return

    class IniSection:

        def __init__(self, name, values):
            self.name = name
            self.values = values

        def __getitem__(self, key_name):
            for key in self.values:
                if key == key_name:
                    return self.values[key]
            raise KeyError

    def _raw_list(self, path):
        """Returns a unprocessed list of all lines in (ini-)file.

        :param path: Path to file
        :type path: str
        """
        with open(path, "r") as f:
            raw_input = f.read()
        # Read all non-empty lines into list
        return [i for i in raw_input.split("\n") if i != ""]

    @classmethod
    def parse(self, path):
        """Parses ini-styled file into an IniObject.

        :param path: Path to file.
        :type path: str
        :return: A :class:`PythonIni` object with the content of read
            ini file.
        :rtype: PythonIni
        """
        lines = self._raw_list(self, path)
        ini = self.PythonIni()
        i = 0
        while True:
            if i == len(lines):
                break
            line = lines[i]
            if line[0] == ";":  # Ini comment -> ignore
                continue
            if "[" in line and "]" in line:
                name = line.strip("[]")
                values = {}
                while True:
                    i += 1
                    if i == len(lines):
                        break
                    line = lines[i]
                    if line[0] == ";":
                        continue
                    if "[" in line and "]" in line:
                        break
                    x, y = line.split("=")
                    values[x] = y.strip('"')
                ini.sections.append(self.IniSection(name, values))
        return ini

    @classmethod
    def to_dict(self, path, sectioned=True):
        """Parses ini-styled file into a dictionary.

        :param path: Path to file.
        :type path: str
        :param sectioned: If True, will create nested dict with inner
            dicts for each section in the ini file. Defaults to 'True'
        :type sectioned: bool, optional
        :return: A dictionary containing all keys in the ini-file
        :rtype: dict
        """
        ini_object = self.parse(path)
        return ini_object.to_dict(sectioned)

    @classmethod
    def to_ini(self, of, dict_in, makedirs=False):
        """Writes a python dict to an ini-styled file.

        :param of: Path to output file
        :type of: str
        :param dict_in: Dictionary to be written
        :type dict_in: dict
        :param makedirs: If 'True', create all necessary directories.
            Defaults to 'False'
        :type makedirs: bool, optional
        """
        i = 0
        sections = False
        of_str = ("")     # Output string
        keys = list(dict_in.keys())
        while True:
            if i == len(dict_in):
                break
            if isinstance(dict_in[keys[i]], dict):
                of_str += f"[{keys[i]}]\n"   # Section header
                dict_keys = dict_in[keys[i]]
                for key in dict_keys:
                    if isinstance(dict_keys[key], dict):
                        raise ValueError(("Too many dimensions in dict -- "
                                          "INI doesn't support subsections."))
                    of_str += f"{key}={dict_keys[key]}\n"
                i += 1
                continue
            of_str += f"{keys[i]}={dict_in[keys[i]]}\n"
            i += 1
        if makedirs:
            hard_write(of, of_str)
            return
        with open(of, "w") as f:
            f.write(of_str)
