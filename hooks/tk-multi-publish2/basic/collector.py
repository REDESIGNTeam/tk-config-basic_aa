# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# This is a dictionary of file type info that allows the basic collector to
# identify common production file types and associate them with a display name,
# item type, and config icon.
COMMON_FILE_INFO = {
    "Alembic Cache": {
        "extensions": ["abc"],
        "icon": "alembic.png",
        "item_type": "file.alembic",
    },
    "3dsmax Scene": {
        "extensions": ["max"],
        "icon": "3dsmax.png",
        "item_type": "file.3dsmax",
    },
    "Hiero Project": {
        "extensions": ["hrox"],
        "icon": "hiero.png",
        "item_type": "file.hiero",
    },
    "Houdini Scene": {
        "extensions": ["hip", "hipnc"],
        "icon": "houdini.png",
        "item_type": "file.houdini",
    },
    "Maya Scene": {
        "extensions": ["ma", "mb"],
        "icon": "maya.png",
        "item_type": "file.maya",
    },
    "Nuke Script": {
        "extensions": ["nk"],
        "icon": "nuke.png",
        "item_type": "file.nuke",
    },
    "Photoshop Image": {
        "extensions": ["psd", "psb"],
        "icon": "photoshop.png",
        "item_type": "file.photoshop",
    },
    "Rendered Image": {
        "extensions": ["dpx", "exr"],
        "icon": "image_sequence.png",
        "item_type": "file.image",
    },
    "Texture": {
        "extensions": ["tiff", "tx", "tga", "dds"],
        "icon": "image.png",
        "item_type": "file.texture",
    },
}


class BasicSceneCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.
    """

    def process_current_scene(self, parent_item):
        """
        Analyzes the current scene open in a DCC and parents a subtree of items
        under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # default implementation does not do anything
        pass

    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze
        :returns: The main item that was created
        """

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        # handle files and folders differently
        if os.path.isdir(path):
            item = self._collect_folder(parent_item, path)
        else:
            item = self._collect_file(parent_item, path)

        return item

    def _collect_file(self, parent_item, path):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :returns: The item that was created
        """

        publisher = self.parent
        publisher.logger.debug("Collecting file: %s" % (path,))

        # get info for the extension
        item_info = self._get_item_info(path)
        item_type = item_info["item_type"]

        # create and populate the item
        file_item = parent_item.create_item(
            item_type,
            item_info["type_display"],
            item_info["display_name"]
        )
        file_item.set_icon_from_path(item_info["icon_path"])

        # if the supplied path is an image, use the original path to generate
        # the thumbnail. type could also be "file.image.sequence" so we won't
        # use the evaluated path which could include a frame format spec
        if (item_type.startswith("file.image") or
            item_type.startswith("file.texture")):
            file_item.set_thumbnail_from_path(path)

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing. we'll use the
        # evaluated path in case it was altered to account for frame sequence
        file_item.properties["path"] = item_info["path"]

        return file_item

    def _collect_folder(self, parent_item, folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """

        publisher = self.parent
        publisher.logger.debug("Collecting folder: %s" % (folder,))

        folder_info = publisher.util.get_file_path_components(folder)

        # create and populate an item for the folder
        folder_item = parent_item.create_item(
            "file.folder",
            "Folder",
            folder_info["filename"]
        )

        # look for icon one level up from this hook's folder
        folder_item.set_icon_from_path(
            self._get_icon_path("folder.png"))

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing
        folder_item.properties["path"] = folder

        return folder_item

    def _get_item_info(self, path):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param path: The file path to identify type info for

        :return: A dictionary of information about the item to create::

            # path = "/path/to/some/file.0001.exr"

            {
                "item_type": "file.image.sequence",
                "type_display": "Rendered Image Sequence",
                "display_name": "file.%04d.exr",
                "icon_path": "/path/to/some/icons/folder/image_sequence.png",
                "path": "/path/to/some/file.%04d.exr"
            }

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """

        publisher = self.parent

        # we may modify the path during this process. use the supplied path as
        # the default value though.
        evaluated_path = path

        # extract the components of the supplied path
        file_info = publisher.util.get_file_path_components(path)
        extension = file_info["extension"]
        filename = file_info["filename"]

        # default values used if no specific type can be determined
        type_display = "File"
        item_type = "file.unknown"
        icon_name = "file.png"
        display_name = filename

        # keep track if a common type was identified for the extension
        common_type_found = False

        # look for the extension in the common file type info dict
        for display in COMMON_FILE_INFO:
            type_info = COMMON_FILE_INFO[display]

            if extension in type_info["extensions"]:
                # found the extension in the common types lookup. extract the
                # item type, icon name.
                type_display = display
                item_type = type_info["item_type"]
                icon_name = type_info["icon"]
                common_type_found = True
                break

        if not common_type_found:
            # no common type match. try to use the mimetype category. this will
            # be a value like "image/jpeg" or "video/mp4". we'll extract the
            # portion before the "/" and use that for display.
            (category_type, _) = mimetypes.guess_type(filename)

            if category_type:
                # the category portion of the mimetype
                category = category_type.split("/")[0]

                type_display = "%s File" % (category.title(),)
                item_type = "file.%s" % (category,)
                icon_name = "%s.png" % (category,)

        # at this point, we should have what we need. do one more check on image
        # file types to see if the path looks like an image sequence.
        if "Image" in type_display:
            # not an ideal way to identify image types, but should work for now.
            # see if this looks like an image sequence.
            img_seq_path = publisher.util.get_image_sequence_path(path)
            if img_seq_path:
                # the supplied image path is part of a sequence. alter the
                # type info to account for this.
                evaluated_path = img_seq_path
                type_display = "%s Sequence" % (type_display,)
                item_type = "%s.%s" % (item_type, "sequence")
                icon_name = "image_sequence.png"

        # construct a full path to the icon given the name defined above
        icon_path = self._get_icon_path(icon_name)

        # everything should be populated. return the dictionary
        return dict(
            item_type=item_type,
            type_display=type_display,
            display_name=display_name,
            icon_path=icon_path,
            path=evaluated_path
        )

    def _get_icon_path(self, icon_name):
        """
        Helper to get the full path to an icon one level up in an "icons"
        folder. If the supplied icon_name doesn't exist there, fall back to the
        file.png icon.
        """
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            icon_name
        )

        # supplied file name doesn't exist. return the default file.png image
        if not os.path.exists(icon_path):
            icon_path = os.path.join(
                self.disk_location,
                os.pardir,
                "icons",
                "file.png"
            )

        return icon_path