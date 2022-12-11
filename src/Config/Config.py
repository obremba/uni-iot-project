from configparser import ConfigParser


class Config:
    def __init__(self, filename='config.ini'):
        self.config = ConfigParser()
        self.filename = filename
        self.read()

    @property
    def factory_url(self):
        return self.config.get('factory', 'opcua_url')

    def has_agent_connection_string(self, agent_name):
        return self.config.has_option('agent', agent_name)

    def get_agent_connection_string(self, agent_name):
        return self.config.get('agent', agent_name)

    def set_agent_connection_string(self, agent_name, connection_string):
        self.config.set('agent', agent_name, connection_string)
        self.write()

    def read(self):
        edited = False
        self.config.read(self.filename)

        if not self.config.has_section('agent'):
            self.config.add_section('agent')

        if not self.config.has_section('factory'):
            self.config.add_section('factory')

        if not self.config.has_option('factory', 'opcua_url'):
            edited = True
            self.config.set('factory', 'opcua_url', input('Podaj adres serwera OPC UA: '))

        if edited:
            self.write()

    def write(self):
        with open(self.filename, 'w') as configFile:
            self.config.write(configFile)
