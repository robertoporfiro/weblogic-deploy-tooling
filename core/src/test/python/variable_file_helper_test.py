"""
Copyright (c) 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""
import unittest

import wlsdeploy.util.variables as variables
import wlsdeploy.tool.util.variable_file_helper as variable_file_helper
from wlsdeploy.tool.util.variable_file_helper import VariableFileHelper
from wlsdeploy.util.model_translator import FileToPython


class VariableFileHelperTest(unittest.TestCase):
    _resources_dir = '../../test-classes'
    _variable_file = _resources_dir + '/variables.properties'
    _model_file = _resources_dir + '/variable_insertion.yaml'
    _variable_helper_keyword = 'variable_helper_keyword.json'
    _variable_helper_custom = 'variable_helper_custom.json'

    def setUp(self):
        self.name = VariableFileHelperTest
        self._model = FileToPython(self._model_file).parse()
        self._helper = VariableFileHelper(self._model, None, '12.2.1.3')

    def testSingleVariableReplacement(self):
        replacement_list = ['topology:Machine.NodeManager.ListenAddress']
        expected = dict()
        expected['/Machine/machine1/NodeManager/ListenAddress'] = '127.0.0.1'
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)

    def testMultiplesReplacement(self):
        expected = dict()
        # expected['server-AdminServer-listenport'] = 9001
        # expected['server-AdminServer-ssl-listenport'] = 9002
        # expected['server-m2-listenport'] = 9005
        # expected['server-m1-listenport'] = 9003
        # expected['server-m1-ssl-listenport'] = 9004
        # expected['server-m2-ssl-listenport'] = 9006
        # expected['jmssystemresource-MyJmsModule-jmsresource-foreignserver-MyForeignServer-connectionurl'] \
        #     = 't3://my.other.cluster:7001'
        # expected['jmssystemresource-MyJmsModule-jmsresource-foreignserver-MyForeignServer-'
        #          'foreigndestination-MyRemoteQ-localjndiname'] = 'jms/remoteQ'
        expected['/Server/AdminServer/SSL/ListenPort'] = '9002'
        expected['/Server/AdminServer/ListenPort'] = '9001'
        expected['/Server/m2/ListenPort'] = '9005'
        expected['/Server/m1/ListenPort'] = '9003'
        expected['/Server/m1/SSL/ListenPort'] = '9004'
        expected['/Server/m2/SSL/ListenPort'] = '9006'
        expected['/JMSSystemResource/MyJmsModule/JmsResource/ForeignServer/MyForeignServer/ConnectionURL'] \
            = 't3://my.other.cluster:7001'
        expected['/JMSSystemResource/MyJmsModule/JmsResource/ForeignServer/MyForeignServer/'
                 'ForeignDestination/MyRemoteQ/LocalJNDIName'] = 'jms/remoteQ'
        #'resources:JMSSystemResource.JmsResource.ForeignDestination.LocalJNDIName',
        replacement_list = ['topology:Server.ListenPort',
                            'resources:JMSSystemResource.JmsResource.ForeignServer.ConnectionURL',
                            'resources:JMSSystemResource.JmsResource.ForeignServer.ForeignDestination.LocalJNDIName',
                            'topology:Server.SSL.ListenPort']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)

    def testInvalidMBeanNameNoException(self):
        expected = dict()
        replacement_list = ['resources:JmsSystemResource.Notes']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)

    def testInvalidAttributeName(self):
        expected = dict()
        replacement_list = ['topology:Server.listenaddress']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)

    def testInvalidSection(self):
        expected = dict()
        replacement_list = ['topologies:Server.ListenAddress']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)

    def testDomainAttributeReplacementAndModel(self):
        expected = dict()
        expected['/Notes'] = 'Test note replacement'
        expected_replacement = '@@PROP:/Notes@@'
        replacement_list = ['topology:Notes']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)
        self.assertEqual(expected_replacement, self._model['topology']['Notes'])

    def testWithSegment(self):
        expected = dict()
        expected['/JDBCSystemResource/Database1/JdbcResource/JDBCDriverParams/URL'] = \
            'jdbc:oracle:thin:@//den00chv.us.oracle.com:1521/PDBORCL'
        expected['/JDBCSystemResource/Database2/JdbcResource/JDBCDriverParams/URLHost'] = \
            'slc05til.us.oracle.com'
        expected['/JDBCSystemResource/Database2/JdbcResource/JDBCDriverParams/URLPort'] = \
            '1521'
        replacement_list = [
            'resources:JDBCSystemResource.JdbcResource.JDBCDriverParams.URL(Port:(?<=PORT=)[\w.-]+(?=\)))',
            'resources:JDBCSystemResource.JdbcResource.JDBCDriverParams.URL(Host:(?<=HOST=)[\w.-]+(?=\)))']
        actual = self._helper.process_variable_replacement(replacement_list)
        self._compare_to_expected_dictionary(expected, actual)
        db2 = 'jdbc:oracle:thin:@(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)' \
              '(HOST=@@PROP:/JDBCSystemResource/Database2/JdbcResource/JDBCDriverParams/URLHost@@)' \
              '(PORT=@@PROP:/JDBCSystemResource/Database2/JdbcResource/JDBCDriverParams/URLPort@@)))' \
              '(CONNECT_DATA=(SERVICE_NAME=orcl.us.oracle.com)))'
        db1 = '@@PROP:/JDBCSystemResource/Database1/JdbcResource/JDBCDriverParams/URL@@'
        self.assertEqual(db2, self._model['resources']['JDBCSystemResource']['Database2']['JdbcResource'][
            'JDBCDriverParams']['URL'])
        self.assertEqual(db1, self._model['resources']['JDBCSystemResource']['Database1']['JdbcResource'][
            'JDBCDriverParams']['URL'])

    def testWithSegmentInDictionary(self):
        expected = dict()
        expected['/MailSession/MailSession-0/PropertiesSmtpHost'] = 'stbeehive.oracle.com'
        expected['/MailSession/MyMailSession/PropertiesSmtpHost'] = 'stbeehive.oracle.com'
        expected['/MailSession/MailSession-0/PropertiesImapHost'] = 'stbeehive.oracle.com'
        expected['/MailSession/MyMailSession/PropertiesImapHost'] = 'stbeehive.oracle.com'
        replacement_list = ["resources:MailSession.Properties[SmtpHost:mail.smtp.host]",
                            "resources:MailSession.Properties[ImapHost:mail.imap.host]"]
        actual = self._helper.process_variable_replacement(replacement_list)
        print 'actual=', actual
        self._compare_to_expected_dictionary(expected, actual)
        self.assertEqual('@@PROP:/MailSession/MyMailSession/PropertiesSmtpHost@@',
                         self._model['resources']['MailSession']['MyMailSession']['Properties']['mail.smtp.host'])
        self.assertEqual('@@PROP:/MailSession/MyMailSession/PropertiesImapHost@@',
                         self._model['resources']['MailSession']['MyMailSession']['Properties']['mail.imap.host'])

    def testWithSegmentInDictionaryAndAPattern(self):
        expected = dict()
        expected['/MailSession/MyMailSession/PropertiesHost'] = 'stbeehive.oracle.com'
        expected['/MailSession/MailSession-0/PropertiesHost'] = 'stbeehive.oracle.com'
        replacement_list = ['resources:MailSession.Properties[Host:(?<=\w.)host]']
        actual = self._helper.process_variable_replacement(replacement_list)
        print 'actual2=', actual
        self._compare_to_expected_dictionary(expected, actual)
        self.assertEqual('@@PROP:/MailSession/MyMailSession/PropertiesHost@@',
                         self._model['resources']['MailSession']['MyMailSession']['Properties']['mail.imap.host'])
        self.assertEqual('@@PROP:/MailSession/MyMailSession/PropertiesHost@@',
                         self._model['resources']['MailSession']['MyMailSession']['Properties']['mail.host'])
        self.assertEqual('@@PROP:/MailSession/MyMailSession/PropertiesHost@@',
                         self._model['resources']['MailSession']['MyMailSession']['Properties']['mail.smtp.host'])

    def testWithVariableHelperKeywords(self):
        expected = dict()
        expected['/JMSSystemResource/MyJmsModule/JmsResource/ForeignServer/MyForeignServer/ConnectionURL'] \
            = 't3://my.other.cluster:7001'
        expected['/Server/AdminServer/ListenPort'] = '9001'
        expected['/Server/m2/ListenPort'] = '9005'
        expected['/Server/m1/ListenPort'] = '9003'
        expected['/Machine/machine1/NodeManager/ListenPort'] = '5557'
        expected['/Machine/machine1/NodeManager/PasswordEncrypted'] = '--FIX ME--'
        expected['/Machine/machine1/NodeManager/UserName'] = 'admin'
        inserted, model, variable_file_name = self._helper.replace_variables_file(
            variable_helper_path_name=self._resources_dir, variable_helper_file_name=self._variable_helper_keyword)
        self.assertEqual(True, inserted)
        self.assertEqual(self._variable_file, variable_file_name)
        actual = variables.load_variables(self._variable_file)
        self._compare_to_expected_dictionary(expected, actual)

    def _compare_to_expected_dictionary(self, expected, actual):
        self.assertEqual(len(expected), len(actual),
                         'Not the same number of entries : expected=' + str(len(expected)) + ', actual=' + str(
                             len(actual)))
        for k, v in actual.iteritems():
            self.assertEqual(True, k in expected and v == expected[k], 'Actual item not in expected ' + k +
                             ' : ' + v + '   expected=' + str(expected))


if __name__ == '__main__':
    unittest.main()