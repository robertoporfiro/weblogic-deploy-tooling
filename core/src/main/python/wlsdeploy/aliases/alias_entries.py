"""
Copyright (c) 2017, 2018, Oracle and/or its affiliates. All rights reserved.
The Universal Permissive License (UPL), Version 1.0
"""
import copy

from oracle.weblogic.deploy.aliases import VersionException
from oracle.weblogic.deploy.aliases import VersionUtils
from oracle.weblogic.deploy.json import JsonException
from oracle.weblogic.deploy.json import JsonStreamTranslator
from oracle.weblogic.deploy.util import FileUtils

import wlsdeploy.aliases.alias_utils as alias_utils
from wlsdeploy.aliases import password_utils
from wlsdeploy.aliases.alias_constants import ChildFoldersTypes
from wlsdeploy.aliases.location_context import LocationContext
from wlsdeploy.aliases.validation_codes import ValidationCodes
from wlsdeploy.aliases.wlst_modes import WlstModes
from wlsdeploy.exception import exception_helper
from wlsdeploy.logging.platform_logger import PlatformLogger
from wlsdeploy.util import dictionary_utils
from wlsdeploy.util.weblogic_helper import WebLogicHelper

from wlsdeploy.aliases.alias_constants import ATTRIBUTES
from wlsdeploy.aliases.alias_constants import CHILD_FOLDERS_TYPE
from wlsdeploy.aliases.alias_constants import CONTAINS
from wlsdeploy.aliases.alias_constants import DEFAULT_NAME_VALUE
from wlsdeploy.aliases.alias_constants import FLATTENED_FOLDER_DATA
from wlsdeploy.aliases.alias_constants import FOLDERS
from wlsdeploy.aliases.alias_constants import GET_MBEAN_TYPE
from wlsdeploy.aliases.alias_constants import GET_METHOD
from wlsdeploy.aliases.alias_constants import MODEL_NAME
from wlsdeploy.aliases.alias_constants import NAME_VALUE
from wlsdeploy.aliases.alias_constants import NONE_CHILD_FOLDERS_TYPE
from wlsdeploy.aliases.alias_constants import SECURITY_PROVIDER_NAME_MAP
from wlsdeploy.aliases.alias_constants import SET_MBEAN_TYPE
from wlsdeploy.aliases.alias_constants import SET_METHOD
from wlsdeploy.aliases.alias_constants import SINGLE
from wlsdeploy.aliases.alias_constants import UNRESOLVED_ATTRIBUTES_MAP
from wlsdeploy.aliases.alias_constants import UNRESOLVED_FOLDERS_MAP
from wlsdeploy.aliases.alias_constants import VERSION
from wlsdeploy.aliases.alias_constants import VERSION_RANGE
from wlsdeploy.aliases.alias_constants import WLST_ATTRIBUTES_PATH
from wlsdeploy.aliases.alias_constants import WLST_CREATE_PATH
from wlsdeploy.aliases.alias_constants import WLST_LIST_PATH
from wlsdeploy.aliases.alias_constants import WLST_MODE
from wlsdeploy.aliases.alias_constants import WLST_NAME
from wlsdeploy.aliases.alias_constants import WLST_NAMES_MAP
from wlsdeploy.aliases.alias_constants import WLST_PATH
from wlsdeploy.aliases.alias_constants import WLST_PATHS
from wlsdeploy.aliases.alias_constants import WLST_SKIP_NAMES
from wlsdeploy.aliases.alias_constants import WLST_SUBFOLDERS_PATH
from wlsdeploy.aliases.alias_constants import WLST_TYPE

IGNORE_FOR_MODEL_LIST = ['DynamicallyCreated', 'Id', 'Tag', 'Tags', 'Type', 'Name']
_class_name = 'AliasEntries'
_logger = PlatformLogger('wlsdeploy.aliases')


class AliasEntries(object):
    """
    The AliasEntries class encapsulates the alias knowledge base structure and resolution mechanisms
    such as determining the values based on whether we are using WLST online or offline, the WLS
    version being used, and the strategy for providing concrete WLST paths from a location context.

    This class is intended only for use by aliases.py.  Other uses of this class violate
    encapsulation and should be avoided.
    """
    __category_modules_dir_name = 'oracle/weblogic/deploy/aliases/category_modules/'
    __domain_category = 'Domain'

    __model_categories_map = {
        'Application': 'AppDeployment',
        'Cluster': 'Cluster',
        'CoherenceClusterSystemResource': 'CoherenceClusterSystemResource',
        'Domain': 'Domain',
        'FileStore': 'FileStore',
        'ForeignJNDIProvider': 'ForeignJNDIProvider',
        'JDBCStore': 'JDBCStore',
        'JDBCSystemResource': 'JDBCSystemResource',
        'JMSBridgeDestination': 'JMSBridgeDestination',
        'JMSServer': 'JMSServer',
        'JMSSystemResource': 'JMSSystemResource',
        'JMX': 'JMX',
        'JTA': 'JTA',
        'Library': 'Library',
        'Log': 'Log',
        'Machine': 'Machine',
        'MailSession': 'MailSession',
        'MessagingBridge': 'MessagingBridge',
        'MigratableTarget': 'MigratableTarget',
        'NMProperties': 'NMProperties',
        'Partition': 'Partition',
        'PartitionWorkManager': 'PartitionWorkManager',
        'PathService': 'PathService',
        'ResourceGroup': 'ResourceGroup',
        'ResourceGroupTemplate': 'ResourceGroupTemplate',
        'ResourceManagement': 'ResourceManagement',
        'ResourceManager': 'ResourceManager',
        'RestfulManagementServices': 'RestfulManagementServices',
        'SAFAgent': 'SAFAgent',
        'Security': 'Security',
        'SecurityConfiguration': 'SecurityConfiguration',
        'SelfTuning': 'SelfTuning',
        'Server': 'Server',
        'ServerTemplate': 'ServerTemplate',
        'ShutdownClass': 'ShutdownClass',
        'StartupClass': 'StartupClass',
        'UnixMachine': 'UnixMachine',
        'VirtualHost': 'VirtualHost',
        'VirtualTarget': 'VirtualTarget',
        'WLDFSystemResource': 'WLDFSystemResource'
    }

    __topology_top_level_folders = [
        'Cluster',
        'JMX',
        'JTA',
        'Log',
        'Machine',
        'MigratableTarget',
        'NMProperties',
        "RestfulManagementServices",
        'Security',
        'SecurityConfiguration',
        'Server',
        'ServerTemplate',
        'UnixMachine',
        'VirtualHost',
        'VirtualTarget'
    ]

    __resources_top_level_folders = [
        'CoherenceClusterSystemResource',
        'FileStore',
        'ForeignJNDIProvider',
        'JDBCStore',
        'JDBCSystemResource',
        'JMSBridgeDestination',
        'JMSServer',
        'JMSSystemResource',
        'MailSession',
        'MessagingBridge',
        'Partition',
        'PartitionWorkManager',
        'PathService',
        'ResourceGroup',
        'ResourceGroupTemplate',
        'ResourceManagement',
        'SAFAgent',
        'SelfTuning',
        'ShutdownClass',
        'StartupClass',
        'WLDFSystemResource'
    ]

    __app_deployments_top_level_folders = [
        'Application',
        'Library'
    ]

    __domain_info_attributes_and_types = {
        'AdminUserName': 'string',
        'AdminPassword': 'password',
        'ServerStartMode': 'string',
        'domainLibraries': 'list',
        # A map of Server Group names to the list of servers/clusters to which they should
        # be targeted.  The ServerGroup must appear in the domain typedef definition.  If
        # the ServerGroup is not listed in this map, it will be targeted to all managed
        # servers in the domain.
        'ServerGroupTargetingLimits': 'dict'
    }

    __domain_name_token = 'DOMAIN'

    def __init__(self, wlst_mode=WlstModes.OFFLINE, wls_version=None):
        """
        The initialization method called when the object is constructed.
        :param wlst_mode: the WLST mode being used, the default is OFFLINE
        :param wls_version: the WLS version to use, the default is the version of WLST being used to run the program.
        """
        self._category_dict = {}
        self._wlst_mode = wlst_mode
        if wls_version is None:
            self._wls_helper = WebLogicHelper(_logger)
            self._wls_version = self._wls_helper.get_actual_weblogic_version()
        else:
            self._wls_helper = WebLogicHelper(_logger, wls_version)
            self._wls_version = wls_version

        if self._wlst_mode == WlstModes.OFFLINE:
            self._requires_security_provider_rename = \
                self._wls_helper.requires_security_provider_rename_in_offline_mode()
        else:
            self._requires_security_provider_rename = False
        return

    def get_dictionary_for_location(self, location, resolve=True):
        """
        Get the alias dictionary for the specified location with all the context applied to the data.  Note
        that any paths in subfolders are not resolved by this method.
        :param location: the location context that identifies the folder in question and the name
                         tokens to use to convert the WLST paths to concrete values
        :return: the alias dictionary for the specified location, or None if the dictionary is not relevant
                 to the current WLS version
        :raises AliasException: if an error occurs while loading or processing the aliases for the specified location
        """
        _method_name = 'get_dictionary_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = self.__get_dictionary_for_location(location, resolve)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return result

    def get_model_domain_subfolder_names(self):
        """
        Get the list of top-level model folder names corresponding to top-level WLST folder names.
        :return:the list of top-level model folder names
        """
        _method_name = 'get_model_domain_subfolder_names'

        _logger.entering(class_name=_class_name, method_name=_method_name)
        folder_list = list(self.__model_categories_map.keys())
        #
        # Remove all folders that do not appear at the WLST root level
        #
        if 'Domain' in folder_list:
            folder_list.remove('Domain')
        if 'ResourceManager' in folder_list:
            folder_list.remove('ResourceManager')

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=folder_list)
        return folder_list

    def get_model_topology_subfolder_names(self):
        """
        Get the top-level model folder names underneath the topology section.
        :return: a list of the folder names
        """
        result = list(self.__topology_top_level_folders)
        if not self._wls_helper.is_weblogic_version_or_above('12.2.1'):
            result.remove('VirtualTarget')
            if not self._wls_helper.is_weblogic_version_or_above('12.1.2'):
                result.remove('RestfulManagementServices')
                result.remove('ServerTemplate')
        return result

    def get_model_resources_subfolder_names(self):
        """
        Get the top-level model folder names underneath the resources section.
        :return: a list of the folder names
        """
        result = list(self.__resources_top_level_folders)
        if not self._wls_helper.is_weblogic_version_or_above('12.2.1'):
            result.remove('Partition')
            result.remove('PartitionWorkManager')
            result.remove('ResourceGroup')
            result.remove('ResourceGroupTemplate')
            result.remove('ResourceManagement')
            if not self._wls_helper.is_weblogic_version_or_above('12.1.2'):
                result.remove('CoherenceClusterSystemResource')
        return result

    def get_model_app_deployments_subfolder_names(self):
        """
        Get the top-level model folder names underneath the appDeployments section.
        :return: a list of the folder names
        """
        return list(self.__app_deployments_top_level_folders)

    def get_domain_info_attribute_names_and_types(self):
        return dict(self.__domain_info_attributes_and_types)

    def get_model_subfolder_names_for_location(self, location):
        """
        Get the list of subfolder names for the specified location.
        :param location: the location context that identifies the folder in question
        :return: the list of subfolder names, or an empty list if there are none
        :raises AliasException: if an error occurs while loading or processing the aliases for the specified location
        """
        _method_name = 'get_model_subfolder_names_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and FOLDERS in folder_dict:
            subfolders_dict = folder_dict[FOLDERS]
            result = list(subfolders_dict.keys())
        else:
            result = list()
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_model_folder_path_for_location(self, location):
        """
        Get a slash delimited string of the path in the model to the specified location.
        :param location: the location context that identifies the folder in question
        :return: the model path string
        :raises AliasException: if an error occurs while loading or processing the aliases for the specified location,
                                or if the location is missing a required name token
        """
        _method_name = 'get_model_folder_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)

        # Initialize return variable
        model_folder_path = ''

        if not location.is_empty():
            location_folders = location.get_model_folders()

            if location_folders[0] in self.get_model_topology_subfolder_names():
                model_folder_path += 'topology:/'
            elif location_folders[0] in self.get_model_resources_subfolder_names():
                model_folder_path += 'resources:/'
            elif location_folders[0] in self.get_model_app_deployments_subfolder_names():
                model_folder_path += 'appDeployments:/'
            elif location_folders[0] == 'domainInfo':
                model_folder_path += 'domainInfo:/'

            my_loc = LocationContext()

            for location_folder in location_folders:
                model_folder_path += '%s/' % location_folder
                my_loc.append_location(location_folder)

                # Have to check for security provider artificial folders that don't have a trailing name token
                if location_folder not in SECURITY_PROVIDER_NAME_MAP:
                    name_token = self.get_name_token_for_location(my_loc)
                    if name_token is not None:
                        name = location.get_name_for_token(name_token)
                        if name is not None:
                            my_loc.add_name_token(name_token, name)
                            model_folder_path += '%s/' % name
                        elif location_folder != location_folders[-1]:
                            # Throw AliasException if name_token is missing
                            # from any location folder, except the last one
                            ex = exception_helper.create_alias_exception('WLSDPLY-08101', str(location), name_token)
                            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                            raise ex

            # Strip off trailing '/' if model_folder_path is not '<section-name>:/'
            if model_folder_path[-2:] != ':/':
                # Strip off trailing '/'
                model_folder_path = model_folder_path[:-1]
        else:
            # Hard to know exactly what to do here but since an empty
            # location is the top-level, just return the location of
            # top-level Domain attributes.
            model_folder_path = 'topology:/'

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_folder_path)

        return model_folder_path

    def get_wlst_attribute_path_for_location(self, location):
        """
        Get the WLST path where the attributes for the specified location are found.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_attribute_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_ATTRIBUTES_PATH)
        result = alias_utils.replace_tokens_in_path(location, tokenized_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_subfolders_path_for_location(self, location):
        """
        Get the WLST path where the subfolders for the specified location are found.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_subfolders_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_SUBFOLDERS_PATH)
        result = alias_utils.replace_tokens_in_path(location, tokenized_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_list_path_for_location(self, location):
        """
        Get the WLST path where to list the existing instances of the type corresponding to the specified location.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_list_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_LIST_PATH)
        result = alias_utils.replace_tokens_in_path(location, tokenized_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_create_path_for_location(self, location):
        """
        Get the WLST path where to create new instances of the type corresponding to the specified location.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_list_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_CREATE_PATH)
        result = alias_utils.replace_tokens_in_path(location, tokenized_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def is_location_child_folder_type(self, location, child_folders_type):
        """
        Does the location folder have the specified child_folders_type?
        :param location: the location
        :param child_folders_type: the ChildFoldersType enum value
        :return: True, if the location folder matches the specified child_folders_type, False otherwise
        :raises: AliasException: if an error occurs while getting the folder for the location or if the
                                 specified type doesn't match and the actual type is 'none'
        """
        _method_name = 'is_location_child_folder_type'

        _logger.entering(str(location), ChildFoldersTypes.from_value(child_folders_type),
                         class_name=_class_name, method_name=_method_name)
        result = False
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and CHILD_FOLDERS_TYPE in folder_dict:
            actual_child_folders_type = folder_dict[CHILD_FOLDERS_TYPE]
            requested_child_folders_type = alias_utils.get_child_folder_type_value_from_enum_value(child_folders_type)
            if requested_child_folders_type == actual_child_folders_type:
                result = True
            elif actual_child_folders_type == NONE_CHILD_FOLDERS_TYPE:
                ex = exception_helper.create_alias_exception('WLSDPLY-08102', location.get_folder_path(),
                                                             ChildFoldersTypes.from_value(child_folders_type))
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
        elif folder_dict is not None and child_folders_type == ChildFoldersTypes.SINGLE:
            # Since SINGLE is the default, if the folder_dict exists but the
            # child_folders_type element doesn't exist, return True
            result = True
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def location_contains_flattened_folder(self, location):
        """
        Does the location folder specified refer to a WLST location that has been flattened to simplify the model?
        :param location: the location
        :return: True, if this location contains a flattened WLST folder, False otherwise
        """
        _method_name = 'location_contains_flattened_folder'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = False
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and FLATTENED_FOLDER_DATA in folder_dict:
            result = True
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_flattened_type_for_location(self, location):
        """
        Get the type of the flattened WLST folder to use to create the folder.
        :param location: the location
        :return: the type of the flattened WLST folder
        """
        _method_name = 'get_wlst_flattened_type_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = None
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and FLATTENED_FOLDER_DATA in folder_dict and \
                WLST_TYPE in folder_dict[FLATTENED_FOLDER_DATA]:
            result = folder_dict[FLATTENED_FOLDER_DATA][WLST_TYPE]
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_flattened_name_for_location(self, location):
        """
        Get the name of the flattened WLST folder to use to create the folder.
        :param location: the location
        :return: the name of the flattened WLST folder
        """
        _method_name = 'get_wlst_flattened_name_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        result = None
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and FLATTENED_FOLDER_DATA in folder_dict and \
                NAME_VALUE in folder_dict[FLATTENED_FOLDER_DATA]:
            result = alias_utils.get_token_value(location, folder_dict[FLATTENED_FOLDER_DATA][NAME_VALUE])
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_flattened_folder_list_path_for_location(self, location):
        """
        Get the WLST path where to list the child folder name of the flattened folder at the specified location.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_flattened_folder_list_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_CREATE_PATH)
        tokenized_child_path = alias_utils.strip_trailing_folders_in_path(tokenized_path, 1)
        result = alias_utils.replace_tokens_in_path(location, tokenized_child_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_wlst_flattened_folder_create_path_for_location(self, location):
        """
        Get the WLST path where to create new instances of the flattened type corresponding to the specified location.
        :param location: the location to use
        :return: the WLST path
        :raises AliasException: if the location is missing required name tokens or
                                the alias data for the location is bad
        """
        _method_name = 'get_wlst_flattened_folder_create_path_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        tokenized_path = self.__get_path_for_location(location, WLST_CREATE_PATH)
        tokenized_child_path = alias_utils.strip_trailing_folders_in_path(tokenized_path, 2)
        result = alias_utils.replace_tokens_in_path(location, tokenized_child_path)
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def get_name_token_for_location(self, location):
        """
        Get the name token for the specified location.
        :param location: the location
        :return: the name token or None, if no new name token is required
        :raises: AliasException: if an error occurs while getting or processing the folder for the specified location
        """
        _method_name = 'get_name_token_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)

        result = None

        if len(location.get_model_folders()) == 0:
            # There are no model folders in the location, so
            # just return %DOMAIN% for the name token
            return self.__domain_name_token

        # Use get_wlst_mbean_type_for_location(location) call
        # to determine if location is VERSION_INVALID, or not.
        if self.get_wlst_mbean_type_for_location(location) is None:
            # This means location is VERSION_INVALID, so just return
            # None for the name_token
            return result

        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None:
            if WLST_ATTRIBUTES_PATH in folder_dict:
                paths_index = folder_dict[WLST_ATTRIBUTES_PATH]
                tokenized_path = \
                    alias_utils.resolve_path_index(folder_dict, paths_index, WLST_ATTRIBUTES_PATH, location)
                last_token = tokenized_path.split('/')[-1]

                if last_token != 'NO_NAME_0' and last_token.startswith('%') and last_token.endswith('%'):
                    token_occurrences = alias_utils.count_substring_occurrences(last_token, tokenized_path)
                    if token_occurrences == 1:
                        result = last_token[1:-1]
            else:
                ex = exception_helper.create_alias_exception('WLSDPLY-08103', location.get_folder_path(),
                                                             WLST_ATTRIBUTES_PATH)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
        else:
            path = location.get_folder_path()

            err_location = LocationContext(location)
            if  not err_location.is_empty():
                folder_name = err_location.pop_location()
                code, message = self.is_valid_model_folder_name_for_location(err_location, folder_name)
                if code == ValidationCodes.VERSION_INVALID:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08130', path,
                                                                 self._wls_helper.get_actual_weblogic_version(),
                                                                 message)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex
            ex = exception_helper.create_alias_exception('WLSDPLY-08131', path,
                                                         self._wls_helper.get_actual_weblogic_version())
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)

        return result

    def get_wlst_mbean_name_for_location(self, location):
        """
        Get the WLST MBean name for the specified location.
        :param location: the location to use
        :return: the WLST MBean name
        :raises AliasException: if an error occurs
        """
        _method_name = 'get_wlst_mbean_name_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)

        mbean_name = None
        if folder_dict is not None:
            if DEFAULT_NAME_VALUE in folder_dict:
                mbean_name = folder_dict[DEFAULT_NAME_VALUE]
            elif WLST_ATTRIBUTES_PATH in folder_dict:
                paths_index = folder_dict[WLST_ATTRIBUTES_PATH]
                tokenized_path = \
                    alias_utils.resolve_path_index(folder_dict, paths_index, WLST_ATTRIBUTES_PATH, location)
                mbean_name = tokenized_path.split('/')[-1]

        if mbean_name is None:
            ex = exception_helper.create_alias_exception('WLSDPLY-08104', location.get_folder_path(),
                                                         DEFAULT_NAME_VALUE, WLST_ATTRIBUTES_PATH)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        if mbean_name.startswith('%') and mbean_name.endswith('%'):
            token_name = mbean_name[1:-1]
            name_tokens = location.get_name_tokens()
            if token_name in name_tokens:
                mbean_name = name_tokens[token_name]
            else:
                ex = exception_helper.create_alias_exception('WLSDPLY-08105', location.get_folder_path(), token_name)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=mbean_name)
        return mbean_name

    def get_wlst_mbean_type_for_location(self, location):
        """
        Get the WLST MBean type for the specified location.
        :param location: the location to use
        :return: the WLST MBean type
        :raises AliasException: if an error occurs
        """
        _method_name = 'get_wlst_mbean_type_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is None:
            wlst_type = None
        elif WLST_TYPE in folder_dict:
            wlst_type = folder_dict[WLST_TYPE]
            if self._requires_security_provider_rename and alias_utils.is_security_provider_location(location) and \
                    wlst_type in SECURITY_PROVIDER_NAME_MAP:
                wlst_type = SECURITY_PROVIDER_NAME_MAP[wlst_type]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08106', location.get_folder_path(), WLST_TYPE)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=wlst_type)
        return wlst_type

    def get_alias_attribute_entries_by_location(self, location):
        """
        Get the attribute entries for the specified location.  Note that since this method does not resolve
        the paths, the wlst_path attribute is removed for the returned attribute entries.
        :param location: the location
        :return: the dictionary of attribute entries, keyed by the model attribute names
        :raises AliasException: if an error occurs
        """
        _method_name = 'get_alias_attribute_entries_by_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        model_attr_dict = dict()
        if folder_dict is not None and ATTRIBUTES in folder_dict:
            attrs = folder_dict[ATTRIBUTES]
            for attr_name in attrs:
                attr = copy.deepcopy(attrs[attr_name])
                if WLST_PATH in attr:
                    del attr[WLST_PATH]
                else:
                    _logger.warning('WLSDPLY-08107', attr_name, location.get_folder_path(), WLST_PATH)
                model_attr_dict[attr_name] = attr
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08108', location.get_folder_path(), ATTRIBUTES)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return model_attr_dict

    def get_alias_attribute_entry_by_model_name(self, location, model_attribute_name):
        """
        Get a single alias attribute entry from the specified location by its model name.
        :param location: the location
        :param model_attribute_name: the model name for the attribute
        :return: the alias entry for the specified attribute
        :raises AliasException: if an error occurs
        """
        _method_name = 'get_alias_attribute_entry_by_model_name'

        _logger.entering(str(location), model_attribute_name, class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and ATTRIBUTES in folder_dict:
            if model_attribute_name in folder_dict[ATTRIBUTES]:
                model_attr_dict = copy.deepcopy(folder_dict[ATTRIBUTES][model_attribute_name])
                if WLST_PATH in model_attr_dict:
                    del model_attr_dict[WLST_PATH]
                else:
                    _logger.warning('WLSDPLY-08107', model_attribute_name, location.get_folder_path(), WLST_PATH)
            else:
                model_attr_dict = None
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08109', model_attribute_name,
                                                         location.get_folder_path(), ATTRIBUTES)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=model_attr_dict)
        return model_attr_dict

    def get_alias_attribute_entry_by_wlst_name(self, location, wlst_attribute_name):
        """
        Get a single alias attribute entry from the specified location by its WLST name.
        :param location: the location
        :param wlst_attribute_name: the WLST name for the attribute
        :return: the alias entry for the specified attribute
        :raises AliasException: if an error occurs
        """
        _method_name = 'get_alias_attribute_entry_by_wlst_name'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        if self._is_wlst_attribute_skipped(folder_dict, wlst_attribute_name):
            result = None
        elif folder_dict is not None and WLST_NAMES_MAP in folder_dict:
            if wlst_attribute_name in folder_dict[WLST_NAMES_MAP]:
                result = copy.deepcopy(folder_dict[WLST_NAMES_MAP][wlst_attribute_name])
                if WLST_PATH in result:
                    del result[WLST_PATH]
                else:
                    _logger.warning('WLSDPLY-08110', wlst_attribute_name, location.get_folder_path(), WLST_PATH)
            else:
                if wlst_attribute_name not in IGNORE_FOR_MODEL_LIST:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08111', location.get_folder_path(),
                                                                 wlst_attribute_name)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex
                else:
                    result = None
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08112', location.get_folder_path(),
                                                         wlst_attribute_name, WLST_NAMES_MAP)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def is_valid_model_folder_name_for_location(self, location, model_folder_name):
        """
        Is the specified model folder name valid for the specified location?
        :param location: the location of the folder's parent
        :param model_folder_name: the model folder name
        :return: the ValidationCode that specifies whether the folder is valid or not.  If the folder is valid
                 but not with in this WLS version and WLST mode, the valid version range is also returned
        :raises: AliasException: if an error occurs
        """
        _method_name = 'is_valid_model_folder_name_for_location'

        _logger.entering(str(location), model_folder_name, class_name=_class_name, method_name=_method_name)
        valid_version_range = None
        if len(location.get_model_folders()) == 0 and model_folder_name in self.get_model_domain_subfolder_names():
            sub_location = LocationContext(location).append_location(model_folder_name)
            folder_dict = self.__get_dictionary_for_location(sub_location, False)
            if folder_dict is None:
                if UNRESOLVED_FOLDERS_MAP in self._category_dict and \
                    model_folder_name in self._category_dict[UNRESOLVED_FOLDERS_MAP]:
                    result = ValidationCodes.VERSION_INVALID
                    valid_version_range = self._category_dict[UNRESOLVED_FOLDERS_MAP][model_folder_name]
                else:
                    result = ValidationCodes.INVALID
            else:
                result = ValidationCodes.VALID
        else:
            folder_dict = self.__get_dictionary_for_location(location, False)

            if folder_dict is None:
                ex = exception_helper.create_alias_exception('WLSDPLY-08113', model_folder_name,
                                                             location.get_folder_path())
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
            elif FOLDERS not in folder_dict:
                ex = exception_helper.create_alias_exception('WLSDPLY-08114', model_folder_name,
                                                             location.get_folder_path())
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

            if model_folder_name in folder_dict[FOLDERS]:
                result = ValidationCodes.VALID
            elif UNRESOLVED_FOLDERS_MAP in folder_dict and model_folder_name in folder_dict[UNRESOLVED_FOLDERS_MAP]:
                result = ValidationCodes.VERSION_INVALID
                valid_version_range = folder_dict[UNRESOLVED_FOLDERS_MAP][model_folder_name]
            else:
                result = ValidationCodes.INVALID
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=[result, valid_version_range])
        return result, valid_version_range

    def is_version_valid_location(self, location):
        """
        Verify that the specified location is valid for the WLS version
        being used.

        Caller needs to determine what action (e.g. log, raise exception,
        continue processing, record validation item, etc.) to take, when
        return code is VERSION_INVALID.

        :param location: the location to be checked
        :return: A ValidationCodes Enum value of either VERSION_INVALID or VALID
        :return: A message saying which WLS version location is valid in, if
                return code is VERSION_INVALID
        """
        _method_name = 'is_version_valid_location'

        _logger.entering(str(location),class_name=_class_name, method_name=_method_name)

        code = ValidationCodes.VALID
        message = ''
        if self.get_wlst_mbean_type_for_location(location) is None:
            model_folder_path = self.get_model_folder_path_for_location(location)
            message = exception_helper.get_message('WLSDPLY-08138', model_folder_path,
                                                   self._wls_helper.get_weblogic_version())
            code = ValidationCodes.VERSION_INVALID

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=[code, message])

        return code, message

    def is_valid_model_attribute_name_for_location(self, location, model_attribute_name):
        """
        Is the specified model attribute name valid for the specified location?
        :param location: the location
        :param model_attribute_name: the model attribute name
        :return: the ValidationCode that specifies whether the attribute is valid or not.  If the attribute is valid
                 but not with in this WLS version and WLST mode, the valid version range is also returned
        :raises: AliasException: if an error occurs
        """
        _method_name = 'is_valid_model_attribute_name_for_location'

        _logger.entering(str(location), model_attribute_name, class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, True)
        valid_version_range = None
        if folder_dict is None:
            result = ValidationCodes.VERSION_INVALID
            valid_version_range = self.__get_valid_version_range_for_folder(location)
        elif ATTRIBUTES in folder_dict:
            if model_attribute_name in folder_dict[ATTRIBUTES]:
                result = ValidationCodes.VALID
            elif model_attribute_name in folder_dict[UNRESOLVED_ATTRIBUTES_MAP]:
                result = ValidationCodes.VERSION_INVALID
                valid_version_range = folder_dict[UNRESOLVED_ATTRIBUTES_MAP][model_attribute_name]
            else:
                result = ValidationCodes.INVALID
        else:
            result = ValidationCodes.INVALID
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=[result, valid_version_range])
        return result, valid_version_range

    ###########################################################################
    #                         Private helper methods                          #
    ###########################################################################

    def _unit_test_only_get_category_map_files(self):
        """
        Internal method used to get the category files for unit testing.

        DO NOT USE!
        :return: blob of stuff
        """
        result = {}
        for key, value in self.__model_categories_map.iteritems():
            category_file_name = '%s.json' % value
            category_file_path = '%s%s' % (self.__category_modules_dir_name, category_file_name)
            result[key] = category_file_path
        return result

    def __get_dictionary_for_location(self, location, resolve_path_tokens=True):
        """
        Get the dictionary for a location with or without path tokens resolved
        :param location: the location
        :param resolve_path_tokens: whether or not to resolve path tokens
        :return: the dictionary
        :raises: AliasException: if an error occurs
        """
        _method_name = '__get_dictionary_for_location'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        if location is None:
            ex = exception_helper.create_alias_exception('WLSDPLY-08115')
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        location_folders = location.get_model_folders()
        if len(location_folders) == 0:
            model_category_name = self.__domain_category
        else:
            model_category_name = location_folders[0]
            if model_category_name not in self.__model_categories_map:
                ex = exception_helper.create_alias_exception('WLSDPLY-08116', model_category_name)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

        category_dict = self.__get_category_dictionary(model_category_name)
        if category_dict is not None and len(location_folders) > 0:
            path_name = '/' + location_folders[0]
            location_subfolders = list(location_folders[1:])
            child_dict = category_dict
            for location_subfolder in location_subfolders:
                if FOLDERS in child_dict and location_subfolder in child_dict[FOLDERS]:
                    child_dict = child_dict[FOLDERS][location_subfolder]
                else:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08117', location_subfolder, path_name)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex
                if child_dict is None:
                    break
                path_name += '/' + location_subfolder

            if resolve_path_tokens:
                resolved_dict = alias_utils.resolve_path_tokens(location, path_name, child_dict)
            else:
                resolved_dict = child_dict
        else:
            resolved_dict = category_dict

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return resolved_dict

    def __get_category_dictionary(self, model_category_name):
        """
        Get the category dictionary from the cache, loading it first if required.  The dictionary
        will be specific to the WLS version and WLST mode in use but the path tokens are not yet resolved.
        :param model_category_name: the category name
        :return: the category dictionary, or None if the category is not relevant to the current WLS version
        :raises: AliasException: if an error occurs while loading the category dictionary
        """
        if model_category_name not in self._category_dict:
            self.__load_category(model_category_name)
        return self._category_dict[model_category_name]

    def __load_category(self, model_category_name):
        """
        Load the category and apply WLS version and WLST mode context to it.
        :param model_category_name: the category name
        :raises: AliasException: if an error occurs
        """
        _method_name = '__load_category'

        _logger.entering(model_category_name, class_name=_class_name, method_name=_method_name)
        model_category_file = self.__model_categories_map[model_category_name]
        raw_category_dict = self.__load_category_file(model_category_file)
        _logger.fine('WLSDPLY-08118', model_category_name, class_name=_class_name, method_name=_method_name)

        # At this point, we need to look for contains elements and replace them accordingly.
        self.__load_contains_categories(model_category_name, raw_category_dict)

        # Now that the structure and paths are updated based on loading contains references,
        # process the folder recursively and resolve everything based on WLS version and WLST mode.
        self._category_dict[model_category_name] = \
            self.__apply_wlst_context_changes(model_category_name, raw_category_dict, self._category_dict)
        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return

    def __load_category_file(self, category_base_file_name):
        """
        Load the category from its data file.
        :param category_base_file_name: the data file base name
        :return: the raw dictionary loaded from the data file
        :raises: AliasException: if an error occurs
        """
        _method_name = '__load_category_file'

        _logger.entering(category_base_file_name, class_name=_class_name, method_name=_method_name)
        category_file_name = '%s.json' % category_base_file_name
        category_file_path = '%s%s' % (self.__category_modules_dir_name, category_file_name)

        _logger.fine('WLSDPLY-08119', category_base_file_name, category_file_path,
                     class_name=_class_name, method_name=_method_name)
        category_input_stream = FileUtils.getResourceAsStream(category_file_path)
        if category_input_stream is None:
            ex = exception_helper.create_alias_exception('WLSDPLY-08120', category_file_path)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        try:
            json_translator = JsonStreamTranslator(category_file_name, category_input_stream)
            result = json_translator.parse()
        except JsonException, jex:
            ex = exception_helper.create_alias_exception('WLSDPLY-08121', category_file_path,
                                                         jex.getLocalizedMessage(), error=jex)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return result

    def __load_contains_categories(self, model_category_name, raw_model_dict, base_path=""):
        """
        Look at the raw dictionary loaded from disk to see if it contains any other model categories
        and load accordingly into the folders element of the dictionary.
        :param model_category_name: the model name of the folder being processed
        :param raw_model_dict: the raw dictionary for the folder being processed
        :param base_path: the base path prefix to add
        :raises: AliasException: if an error occurs loading or processing the alias entries
        """
        _method_name = '__load_contains_categories'

        _logger.entering(model_category_name, class_name=_class_name, method_name=_method_name)
        if FOLDERS in raw_model_dict:
            raw_model_dict_folders = raw_model_dict[FOLDERS]
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08006', FOLDERS, model_category_name)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        #
        # If the base_path is not empty, got fix up the wlst_paths for this dictionary and then
        # recursively call the method on each folder until all non-contained paths are updated.
        #
        if len(base_path) > 0:
            if WLST_PATHS in raw_model_dict:
                raw_folders_wlst_paths = raw_model_dict[WLST_PATHS]
                for key, value in raw_folders_wlst_paths.iteritems():
                    raw_model_dict[WLST_PATHS][key] = base_path + value

            for folder in raw_model_dict_folders:
                raw_folder_dict = raw_model_dict_folders[folder]
                self.__load_contains_categories(folder, raw_folder_dict, base_path)

        #
        # Now that the folder paths are all updated accordingly, load any contains folders, compute the
        # new path, and recursively call the method to update all of their paths.  After processing the
        # entire contains section and loading it into the folders, delete the contains section.
        #
        if CONTAINS in raw_model_dict:
            new_base_path = alias_utils.compute_base_path(model_category_name, raw_model_dict)

            contained_folders = raw_model_dict[CONTAINS]
            for contained_folder in contained_folders:
                if contained_folder in self.__model_categories_map:
                    folder_file = self.__model_categories_map[contained_folder]
                else:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08122', contained_folder, model_category_name)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex
                raw_folder_dict = self.__load_category_file(folder_file)

                self.__load_contains_categories(contained_folder, raw_folder_dict, new_base_path)
                raw_model_dict_folders[contained_folder] = raw_folder_dict
            del raw_model_dict[CONTAINS]

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return

    def __apply_wlst_context_changes(self, path_name, alias_dict, parent_dict):
        """
        Apply the WLS version and WLST mode changes to the alias dictionary so that the resulting
        dictionary is specific to the current WLST context.
        :param path_name: the model folder path name for the alias dictionary
        :param alias_dict: the folder alias dictionary
        :return: the filtered alias dictionary or None if folder is not relevant to the current WLS version
        :raises: AliasException: if an error occurs
        """
        _method_name = '__apply_wlst_context_changes'

        #
        # First, determine if this dictionary is even relevant to the current WLS version.
        #
        if VERSION in alias_dict:
            dict_version_range = alias_dict[VERSION]
            try:
                _logger.finer('WLSDPLY-08123', path_name, dict_version_range,
                              self._wls_helper.get_actual_weblogic_version(),
                              class_name=_class_name, method_name=_method_name)
                if not self.__version_in_range(dict_version_range):
                    _logger.finer('WLSDPLY-08124', path_name, dict_version_range,
                                  self._wls_helper.get_actual_weblogic_version(),
                                  class_name=_class_name, method_name=_method_name)
                    if UNRESOLVED_FOLDERS_MAP not in parent_dict:
                        parent_dict[UNRESOLVED_FOLDERS_MAP] = dict()
                    alias_dict_folder_name = alias_utils.compute_folder_name_from_path(path_name)
                    parent_dict[UNRESOLVED_FOLDERS_MAP][alias_dict_folder_name] = dict_version_range
                    return None
                else:
                    _logger.finer('WLSDPLY-08125', path_name, dict_version_range,
                                  self._wls_helper.get_actual_weblogic_version(),
                                  class_name=_class_name, method_name=_method_name)
            except VersionException, ve:
                ex = exception_helper.create_alias_exception('WLSDPLY-08126', path_name, dict_version_range,
                                                             ve.getLocalizedMessage(), error=ve)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

        result = dict()
        if FOLDERS in alias_dict:
            result_folders = dict()
            folders = alias_dict[FOLDERS]
            for folder in folders:
                folder_dict = self.__apply_wlst_context_changes(path_name + '/' + folder, folders[folder], alias_dict)
                result_folders[folder] = folder_dict
            result[FOLDERS] = result_folders

        if FLATTENED_FOLDER_DATA in alias_dict:
            result_flattened = dict()
            flattened_data = alias_dict[FLATTENED_FOLDER_DATA]
            for key, value in flattened_data.iteritems():
                result_flattened[key] = self._resolve_curly_braces(value)
            result[FLATTENED_FOLDER_DATA] = result_flattened

        if WLST_TYPE in alias_dict:
            result[WLST_TYPE] = self._resolve_curly_braces(alias_dict[WLST_TYPE])

        if CHILD_FOLDERS_TYPE in alias_dict:
            result[CHILD_FOLDERS_TYPE] = alias_dict[CHILD_FOLDERS_TYPE]
        else:
            result[CHILD_FOLDERS_TYPE] = SINGLE

        if DEFAULT_NAME_VALUE in alias_dict:
            result[DEFAULT_NAME_VALUE] = self._resolve_curly_braces(alias_dict[DEFAULT_NAME_VALUE])

        if WLST_PATHS in alias_dict:
            wlst_paths = alias_dict[WLST_PATHS]
            result_wlst_paths = dict()
            for key in wlst_paths:
                result_wlst_paths[key] = self._resolve_curly_braces(wlst_paths[key])
            result[WLST_PATHS] = result_wlst_paths
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08127', path_name)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        if WLST_ATTRIBUTES_PATH in alias_dict:
            result[WLST_ATTRIBUTES_PATH] = self._resolve_curly_braces(alias_dict[WLST_ATTRIBUTES_PATH])
        if WLST_SUBFOLDERS_PATH in alias_dict:
            result[WLST_SUBFOLDERS_PATH] = self._resolve_curly_braces(alias_dict[WLST_SUBFOLDERS_PATH])
        if WLST_LIST_PATH in alias_dict:
            result[WLST_LIST_PATH] = self._resolve_curly_braces(alias_dict[WLST_LIST_PATH])
        if WLST_CREATE_PATH in alias_dict:
            result[WLST_CREATE_PATH] = self._resolve_curly_braces(alias_dict[WLST_CREATE_PATH])

        if ATTRIBUTES in alias_dict:
            result_model_attrs = dict()
            result_wlst_attrs = dict()
            unresolved_attrs = dict()
            wlst_skip_attrs = list()

            model_attrs = alias_dict[ATTRIBUTES]
            for model_attr in model_attrs:
                model_attr_dict, unresolved_version_range = \
                    self.__resolve_attribute_by_wlst_context(path_name, model_attr, model_attrs)
                if model_attr_dict is None:
                    unresolved_attrs[model_attr] = unresolved_version_range
                    continue

                #
                # At this point, the attribute is matched to a single dictionary.  All we
                # need to do is to remove the version and wlst_mode attributes.  We do not
                # resolve and replace the wlst_path value yet since the path tokens cannot
                # yet be replaced.  We will resolve and replace the wlst_path at runtime
                # to make the token replacement more efficient.
                #
                del model_attr_dict[VERSION_RANGE]
                del model_attr_dict[WLST_MODE]

                if WLST_NAME in model_attr_dict:
                    wlst_name = model_attr_dict[WLST_NAME]
                else:
                    ex = exception_helper.create_alias_exception('WLSDPLY-08128', model_attr, path_name)
                    _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                    raise ex

                #
                # To make the reverse lookup map usable, we need to add the model attribute name to the
                # model_attr_dict.  Otherwise, it is impossible to find the model attribute name when
                # looking up the attribute by the WLST name.
                #
                model_attr_dict[MODEL_NAME] = model_attr
                result_model_attrs[model_attr] = model_attr_dict
                result_wlst_attrs[wlst_name] = model_attr_dict

                # if attribute is dual-password, add its WLST skip name to the skip list
                skip_name = password_utils.get_wlst_skip_name(model_attr_dict, self._wlst_mode)
                if skip_name is not None:
                    wlst_skip_attrs.append(skip_name)

            result[ATTRIBUTES] = result_model_attrs
            result[WLST_NAMES_MAP] = result_wlst_attrs
            result[UNRESOLVED_ATTRIBUTES_MAP] = unresolved_attrs
            result[WLST_SKIP_NAMES] = wlst_skip_attrs

        return result

    def __resolve_attribute_by_wlst_context(self, path_name, attr_name, attrs_dict):
        """
        Find the attribute list element that applies to the current WLS version and WLST mode.

        :param path_name: the model folder path name foe the attribute
        :param attr_name: the model attribute name
        :param attrs_dict: the attributes dictionary
        :return: the matched and unmatched attribute dictionaries, one of which will always be None
                 depending on whether or not a match was found.
        :raises: AliasException: if an error occurs
        """
        _method_name = '__resolve_attribute_by_wlst_context'

        _logger.entering(path_name, attr_name, class_name=_class_name, method_name=_method_name)
        attr_array = attrs_dict[attr_name]
        matches = list()

        version_range_dict = dict()
        for attr_dict in attr_array:
            if WLST_MODE not in attr_dict:
                ex = exception_helper.create_alias_exception('WLSDPLY-08129', attr_name, path_name, attr_dict)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex
            elif VERSION_RANGE not in attr_dict:
                ex = exception_helper.create_alias_exception('WLSDPLY-08130', attr_name, path_name, attr_dict)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

            attr_dict_wlst_mode = attr_dict[WLST_MODE]
            attr_dict_version_range = attr_dict[VERSION_RANGE]
            alias_utils.update_version_range_dict(version_range_dict, attr_dict_wlst_mode, attr_dict_version_range)

            if not self.__wlst_mode_matches(attr_dict_wlst_mode):
                continue

            try:
                _logger.finer('Testing {0}/{1} with {2}', path_name, attr_name, attr_dict_version_range,
                              class_name=_class_name, method_name=_method_name)
                if self.__version_in_range(attr_dict_version_range):
                    matches.append(attr_dict)
            except VersionException, ve:
                ex = exception_helper.create_alias_exception('WLSDPLY-08217', attr_name, path_name,
                                                             attr_dict_version_range, ve.getLocalizedMessage(),
                                                             error=ve)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

        matched_attr = None
        unmatched_attr = None
        if len(matches) == 1:
            matched_attr = matches[0]
            matched_attr = self.__resolve_attribute(matched_attr)
        elif len(matches) == 0:
            unmatched_attr = self.__get_unmatched_attribute_version_range(version_range_dict)
            _logger.finer('WLSDPLY-08140', attr_name, path_name, self._wls_version,
                          WlstModes.from_value(self._wlst_mode), unmatched_attr,
                          class_name=_class_name, method_name=_method_name)
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08141', attr_name, path_name, self._wls_version,
                                                         WlstModes.from_value(self._wlst_mode))
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name)
        return matched_attr, unmatched_attr

    def __wlst_mode_matches(self, attr_mode_string):
        """
        Does the specified WLST mode match the current context?
        :param attr_mode_string: the specified WLST mode string
        :return: true if the string is a match, false otherwise
        """
        return attr_mode_string == 'both' or attr_mode_string == WlstModes.from_value(self._wlst_mode).lower()

    def __version_in_range(self, attr_version_range):
        """
        Does the current WLS version fall within the specified version range?
        :param attr_version_range: the specified version range
        :return: true if the current version is within the range, false otherwise
        :raises: VersionException: if an error occurs in processing the specified version range
        """
        return VersionUtils.isVersionInRange(self._wls_version, attr_version_range)

    def __resolve_attribute(self, attr_dict):
        """
        Process the attribute entry removing the curly braces to allow the correct value based on the current WLST mode.
        :param attr_dict: the attribute entry dictionary
        :return: a modified copy of the attribute entry dictionary
        """
        result = dict()
        for key in attr_dict:
            attr = attr_dict[key]
            if type(attr) is dict:
                result[key] = self.__resolve_attribute(attr)
            else:
                result[key] = self._resolve_curly_braces(attr)

        for key in [GET_METHOD, SET_METHOD, GET_MBEAN_TYPE, SET_MBEAN_TYPE]:
            if key in result and len(result[key]) == 0:
                del result[key]
        return result

    # Using single underscore so that it is accessible to the unit test that verifies the JSON files.
    def _resolve_curly_braces(self, value):
        """
        Remove any curly braces and return the value for the current WLST mode.
        :param value: the original value
        :return: the modified value, or the original if not curly braces were embedded
        """
        str_value = str(value)
        if '${' in str_value:
            parts = alias_utils.parse_curly_braces(str_value)
            return parts[self._wlst_mode]
        return value

    def __get_unmatched_attribute_version_range(self, version_range_dict):
        """
        Get the valid version range for the unmatched attribute.
        :param version_range_dict: the version range dictionary
        :return: the version range for the current WLST mode
        """
        _method_name = '__get_unmatched_attribute_version_range'

        _logger.entering(version_range_dict, class_name=_class_name, method_name=_method_name)
        if self._wlst_mode == WlstModes.OFFLINE:
            if 'offline' in version_range_dict:
                result = version_range_dict['offline']
            else:
                result = None
        elif self._wlst_mode == WlstModes.ONLINE:
            if 'online' in version_range_dict:
                result = version_range_dict['online']
            else:
                result = None
        else:
            result = None
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=result)
        return result

    def __get_valid_version_range_for_folder(self, location):
        """
        Get the valid version range for the folder based on the location.  This method should only
        be called when the folder is not valid in the current version.
        :param location: the location
        :return: the valid version range of the highest level folder that was filtered out
        :raises: AliasException: if the location is not valid or the folder was valid
        """
        _method_name = '__get_valid_version_range_for_folder'

        _logger.entering(str(location), class_name=_class_name, method_name=_method_name)
        version_range = None
        parent_dict = self._category_dict
        path_name = ''

        folders = location.get_model_folders()
        for folder in folders:
            path_name += '/' + folder
            if folder in parent_dict:
                parent_dict = parent_dict[folder]
            elif folder in parent_dict[UNRESOLVED_FOLDERS_MAP]:
                version_range = parent_dict[UNRESOLVED_FOLDERS_MAP][folder]
                break
            else:
                ex = exception_helper.create_alias_exception('WLSDPLY-08142', path_name)
                _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
                raise ex

        if version_range is None:
            ex = exception_helper.create_alias_exception('WLSDPLY-08143', location.get_folder_path(), self._wls_version)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex
        _logger.exiting(class_name=_class_name, method_name=_method_name, result=version_range)
        return version_range

    def _is_wlst_attribute_skipped(self, folder_dict, wlst_attribute_name):
        skip_names = dictionary_utils.get_element(folder_dict, WLST_SKIP_NAMES)  # type: list
        if skip_names is not None:
            return wlst_attribute_name in skip_names
        return False

    def __get_path_for_location(self, location, path_type=WLST_ATTRIBUTES_PATH):
        """
        Get the tokenized path of the specified type for the location.  This method is used by all path-related methods.
        :param location: the location
        :param path_type: the path type
        :return: the path
        :raises: AliasException: if an error occurs because the alias data is missing required fields
        """
        _method_name = '__get_path_for_location'

        _logger.entering(str(location), path_type, class_name=_class_name, method_name=_method_name)
        folder_dict = self.__get_dictionary_for_location(location, False)
        if folder_dict is not None and path_type in folder_dict:
            paths_index = folder_dict[path_type]
            tokenized_path = alias_utils.resolve_path_index(folder_dict, paths_index, path_type, location)
        elif folder_dict is not None and WLST_ATTRIBUTES_PATH in folder_dict:
            paths_index = folder_dict[WLST_ATTRIBUTES_PATH]
            tokenized_attr_path = \
                alias_utils.resolve_path_index(folder_dict, paths_index, WLST_ATTRIBUTES_PATH, location)
            num_dirs_to_strip = alias_utils.get_number_of_directories_to_strip(path_type, WLST_ATTRIBUTES_PATH)
            tokenized_path = alias_utils.strip_trailing_folders_in_path(tokenized_attr_path, num_dirs_to_strip)
        else:
            ex = exception_helper.create_alias_exception('WLSDPLY-08144', location.get_folder_path(),
                                                         WLST_ATTRIBUTES_PATH)
            _logger.throwing(ex, class_name=_class_name, method_name=_method_name)
            raise ex

        _logger.exiting(class_name=_class_name, method_name=_method_name, result=tokenized_path)
        return tokenized_path
