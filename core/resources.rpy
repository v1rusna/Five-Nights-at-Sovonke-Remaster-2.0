init python in v1FNaSR:

    import posixpath as _posixpath

    class Folder(object):
        def __init__(self, name="", parent=None):
            self._name = name
            self._parent = parent
            self._files = {}          # local files only
            self._folders = {}        # name -> folder
            self._cache_files_flat = {}    # recursive file cache
            self._cache_folders_flat = {}  # recursive folder cache

        def add_file(self, name, full_path):
            self._files[name] = full_path

        def __getitem__(self, key):
            return self._files[key]

        def get_or_create_folder(self, name):
            if name not in self._folders:
                self._folders[name] = Folder(name, self)
            return self._folders[name]

        def __getattr__(self, key):
            if key in self._folders:
                return self._folders[key]
            raise AttributeError(key)

        def list_files(self):
            return list(self._files.keys())

        def list_folders(self):
            return list(self._folders.keys())

        def build_cache(self):
            """Рекурсивно строит кеш файлов и папок."""
            self._cache_files_flat = dict(self._files)
            self._cache_folders_flat = {}

            for folder_name, folder in self._folders.items():
                folder.build_cache()

                # cache subfolders
                self._cache_folders_flat[folder_name] = folder
                self._cache_folders_flat.update(folder._cache_folders_flat)

                # cache files
                self._cache_files_flat.update(folder._cache_files_flat)

        # быстрый поиск файла по имени
        def find_file(self, name, default=None):
            return self._cache_files_flat.get(name, default)


        def tree(self, indent=""):
            """Печатает древовидную структуру папок/файлов."""
            renpy.log("----------| FNaSR |----------")
            renpy.log(indent + self._name)

            # files
            for f in sorted(self._files):
                renpy.log(indent + "    ├── " + f)

            # folders
            for i, name in enumerate(sorted(self._folders)):
                folder = self._folders[name]
                last = (i == len(self._folders) - 1)
                branch = "    └── " if last else "    ├── "

                renpy.log(indent + branch + name)
                folder.tree(indent + ("    " if last else "    |"))
            renpy.log("------------------------------")


    class Resources(object):
        """Менеджер ресурсов: изображения, звуки, шрифты."""
        
        def __init__(self, mod_path, images="images", sounds="sounds", fonts="fonts"):
            self.mod_path = mod_path
            self.paths_directors = {
                "images": images,
                "sounds": sounds,
                "fonts": fonts
            }

            self.whitelist_extensions = {
                "images": ["png", "jpg", "jpeg", "webp", "avif", "svg", "bmp", "gif", "tga", "tif", "tiff"],
                "sounds": ["ogg", "opus", "mp3", "wav", "flac", "m4a", "mp2", "aif", "aiff", "mod", "xm", "it", "s3m"],
                "fonts": ["ttf", "otf"]
            }
            
            # корневые папки
            self.images = Folder("images")
            self.sounds = Folder("sounds")
            self.fonts  = Folder("fonts")

            # внутренние индексы
            self._image_index = {}
            self._sound_index = {}
            self._font_index  = {}

            self._initialized = False

        # -------------------------------------------------------

        def init(self):
            if self._initialized:
                return

            files = renpy.list_files()
            self._index_category(self.images, "images", files)
            self._index_category(self.sounds, "sounds", files)
            self._index_category(self.fonts,  "fonts",  files)

            # build caches
            self.images.build_cache()
            self.sounds.build_cache()
            self.fonts.build_cache()

            self._initialized = True

        # -------------------------------------------------------

        def _index_category(self, root_folder, category, files):
            """Строит дерево для конкретной категории."""
            base_dir = _posixpath.join(self.mod_path, self.paths_directors[category])
            prefix = base_dir + "/"

            allowed_ext = self.whitelist_extensions[category]

            for path in files:
                if not path.startswith(prefix):
                    continue

                filename = path.split("/")[-1]
                if "." not in filename:
                    continue

                ext = filename.rsplit(".", 1)[-1].lower()
                if ext not in allowed_ext:
                    continue

                name_no_ext = filename.rsplit(".", 1)[0]

                # относительный путь после категории
                rel = path[len(prefix):]      # dir1/dir2/a.png

                parts = rel.split("/")        # ["dir1", "dir2", "a.png"]
                folders = parts[:-1]          # ["dir1", "dir2"]
                file_name = name_no_ext

                # Проверка конфликтов с методами менеджера
                for f in folders:
                    if hasattr(self, f):
                        raise Exception(
                            "Folder '%s' conflicts with V1ResourcesFNaSR attribute." % f
                        )

                # создаём вложенную цепочку
                folder = root_folder
                for f in folders:
                    folder = folder.get_or_create_folder(f)

                folder.add_file(file_name, path)

                # индекс для быстрого доступа (только для файлов верхнего уровня)
                if category == "images":
                    self._image_index[file_name] = path
                elif category == "sounds":
                    self._sound_index[file_name] = path
                else:
                    self._font_index[file_name] = path

        # -------------------------------------------------------

        def find_image(self, name, default=None):
            return self.images.find_file(name, default)

        def find_sound(self, name, default=None):
            return self.sounds.find_file(name, default)

        def find_font(self, name, default=None):
            return self.fonts.find_file(name, default)

        def get_image(self, name, default=None):
            return self._image_index.get(name, default)

        def get_sound(self, name, default=None):
            return self._sound_index.get(name, default)

        def get_font(self, name, default=None):
            return self._font_index.get(name, default)

        def reload(self):
            self.images = Folder("images")
            self.sounds = Folder("sounds")
            self.fonts  = Folder("fonts")

            self._image_index.clear()
            self._sound_index.clear()
            self._font_index.clear()

            self._initialized = False
            self.init()

        def __repr__(self):
            return "renpy.store.v1FNaSR.Resources(%s)" % self.mod_path

    resources = Resources("FNaSR")
    

















