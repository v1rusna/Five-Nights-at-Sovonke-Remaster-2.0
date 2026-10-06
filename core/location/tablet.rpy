init python in v1FNaSR:
    from math import ceil as _v1ceil
    import string as _string
    from datetime import timedelta as _td

    _MIN_CHARGE = 0

    class EnergyStorage(ResetLogic):
        __slots__ = (
            "_charge", "_max_charge", "_discharge",
        )
        def __init__(self, charge=1000, max_charge=1000, discharge=1):
            charge = int(charge)
            max_charge = int(max_charge)
            discharge = int(discharge)

            if max_charge <= _MIN_CHARGE:
                raise FNaSRValueError("max_charge не может быть меньше или равняться {}".format(_MIN_CHARGE))

            if charge < _MIN_CHARGE or charge > max_charge:
                raise FNaSRValueError("charge должен находиться в диапазоне от '{}' до '{}'".format(_MIN_CHARGE, max_charge))

            self._parent = parent

            self._setattr("_charge", charge)
            self._setattr("_max_charge", max_charge)
            self._setattr("_discharge", discharge)

        @property
        def charge(self):
            return self._charge

        @property
        def charge_percentage(self):
            if self._max_charge == _MIN_CHARGE:
                return 100

            return int(_v1ceil((self._charge - _MIN_CHARGE) / float(self._max_charge - _MIN_CHARGE) * 100))

        @property
        def out_battery(self):
            return self._charge <= _MIN_CHARGE

        @property
        def max_charge(self):
            return self._max_charge

        @property
        def discharge(self):
            return self._discharge

        def safe_charge(self, value):
            value = int(value)
            if value < 0:
                return

            self._charge = max(_MIN_CHARGE, min(self.max_charge, self._charge+value))

        def safe_discharge(self, value):
            value = int(value)
            if value < 0:
                return

            self._charge = max(_MIN_CHARGE, min(self.max_charge, self._charge-value))

        def set_charge(self, new_charge):
            new_charge = int(new_charge)

            if not _MIN_CHARGE <= new_charge <= self._max_charge:
                raise FNaSRValueError("Новый заряд планшета должен находиться в диапазоне от '{}' до '{}'".format(_MIN_CHARGE, self._max_charge))

            self._charge = new_charge

        def set_discharge(self, new_discharge):
            new_discharge = int(new_discharge)

            if new_discharge < 0:
                raise FNaSRValueError("new_discharge не может быть меньше нуля")

            self._discharge = new_discharge

        def charge_from(self, source):
            if not isinstance(source, EnergyStorage):
                raise FNaSRValueError("source должен быть 'EnergyStorage', пришло: {}".format(type(source)))

            if source.out_battery:
                return

            if self._charge >= self._max_charge:
                return

            source.safe_discharge(1)
            self.safe_charge(self._discharge+1)

    # TODO: реализовать павербанк и его использование
    # Он нужен для зарядки планшета, он либо будет заряжен со старта, либо его можно заряжать от генератор, либо забирать заряд у одного планшета и передавать другому
    # То есть игрок идет на локацию с генератором, заряжает павер, возвращается в локацию с планшетом и заряжает планшет
    # После можно сделать кнопку 'инвентарь' который показывает список вещей у игрока, например, а сам экран будет примерно такой:
    # for powerbank in player.inventory:
    #     text "PowerBank({}%)".format(powerbank.capacity_percentage)
    # С появлением EnergyStorage и charge_from у него теперь появляется вопрос
    # Нужен ли мне PowerBank как отдельный класс? Я ведь могу просто написать powerbank = EnergyStorage()
    # разве что для проверки isinstance(item, PowerBank)
    class PowerBank(EnergyStorage):
        def __init__(**kwargs):
            super(PowerBank, self).__init__(**kwargs)

    class TabletNotFound(FNaSRException):
        pass

    class Tablet(GameObject):
        __slots__ = (
            "_tag", "_charge", "_max_charge", "_discharge",
            "_available_locations", "_selected_location_id",
            "_location_id"
        )
        
        def __init__(self, tag, charge=1000, max_charge=1000, discharge=1):
            super(Tablet, self).__init__()
            
            tag = to_text(tag)
            if not tag:
                raise FNaSRValueError("tag не может быть пустым")

            max_charge = int(max_charge)
            charge = int(charge)
            discharge = int(discharge)

            if max_charge <= _MIN_CHARGE:
                raise FNaSRValueError("max_charge не может быть меньше или равняться {}".format(_MIN_CHARGE))

            if charge < _MIN_CHARGE or charge > max_charge:
                raise FNaSRValueError("charge должен находиться в диапазоне от '{}' до '{}'".format(_MIN_CHARGE, max_charge))

            if discharge < 0:
                raise FNaSRValueError("discharge не может быть меньше нуля")

            self._tag = tag

            self._setattr("_charge", charge)
            self._setattr("_max_charge", max_charge)
            self._setattr("_discharge", discharge)

            self._available_locations = set()
            self._selected_location_id = None

            self._location_id = None

        @property
        def tag(self):
            return self._tag

        @property
        def charge(self):
            return self._charge

        @property
        def max_charge(self):
            return self._max_charge

        @property
        def out_battery(self):
            return self._charge <= _MIN_CHARGE

        @property
        def selected(self):
            return self._selected_location_id

        @property
        def location_id(self):
            return self._location_id

        @property
        def charge_percentage(self):
            if self._max_charge == _MIN_CHARGE:
                return 100

            percent = (
                (self._charge - _MIN_CHARGE)
                / float(self._max_charge - _MIN_CHARGE)
                * 100
            )

            return int(_v1ceil(percent))

        @property
        def registered_locations(self):
            return sorted(self._available_locations)

        def get_remaining_time(self):
            if self._charge <= 0:
                return 0.0

            if self._discharge <= 0:
                return float('inf')

            seconds_left = (self._charge / self._discharge) * self.current_refresh_time
            return seconds_left

        def get_formatted_time(self):
            seconds = self.get_remaining_time()
            
            if seconds == float('inf'):
                return "∞"
            
            return str(_td(seconds=round(seconds)))

        def safe_charge(self, value):
            value = int(value)
            if value < 0:
                return

            self._charge = max(_MIN_CHARGE, min(self._max_charge, self._charge+value))

        def safe_discharge(self, value):
            value = int(value)
            if value < 0:
                return

            self._charge = max(_MIN_CHARGE, min(self._max_charge, self._charge-value))

        def set_charge(self, new_charge):
            new_charge = int(new_charge)

            if not _MIN_CHARGE <= new_charge <= self._max_charge:
                raise FNaSRValueError(
                    "Новый заряд планшета должен находиться "
                    "в диапазоне от '{}' до '{}'".format(
                        _MIN_CHARGE,
                        self._max_charge,
                    )
                )

            self._charge = new_charge

        def set_discharge(self, new_discharge):
            new_discharge = int(new_discharge)

            if new_discharge < 0:
                raise FNaSRValueError("new_discharge не может быть меньше нуля")

            self._discharge = new_discharge

        def register(self, location_id):
            location_id = int(location_id)
            self._available_locations.add(location_id)
            if self._selected_location_id is None:
                self._selected_location_id = location_id

        def unregister(self, location_id):
            location_id = int(location_id)
            self._available_locations.discard(location_id)
            if not self._available_locations:
                self._selected_location_id = None
            elif self._selected_location_id == location_id:
                self._selected_location_id = renpy.random.choice(list(self._available_locations))

        def has_location(self, location_id):
            return int(location_id) in self._available_locations

        def connect(self, tablet):
            if not isinstance(tablet, Tablet):
                raise FNaSRTypeError("tablet должен быть 'Tablet', получено '{}'".format(type(tablet)))

            for loc_id in tablet.registered_locations:
                self.register(loc_id)

        def select(self, location_id):
            location_id = int(location_id)

            if location_id not in self._available_locations:
                raise FNaSRValueError("Location '{}' не зарегистрирован в планшете".format(location_id))

            self._selected_location_id = location_id

        def update(self):
            if self._discharge == 0:
                return

            if self._charge <= _MIN_CHARGE:
                return

            self._charge = max(_MIN_CHARGE, min(self._max_charge, self._charge-self._discharge))

            update_ui()

        def reset(self):
            if self._reset_to_default["_location_id"] != self._location_id:
                tm = require_system("tablet")
                if self._reset_to_default["_location_id"] is None:
                    tm.unplace_tablet(self)
                else:
                    tm.move_tablet(self, self._reset_to_default["_location_id"])
            super(Tablet, self).reset()

        def __repr__(self):
            return "Tablet(tag=%r, charge=%r, location_id=%r)" % (
                self._tag, self._charge, self._location_id
            )


    class TabletManager(object):
        def __init__(self):
            self._tablets = {}

        @property
        def tablets(self):
            """Снимок реестра: список всех зарегистрированных Tablet."""
            return list(iter_values(self._tablets))

        def has_tablet(self, tag):
            return to_text(tag) in self._tablets

        def get_tablet(self, tag):
            """Возвращает Tablet или None, если tag не зарегистрирован."""
            return self._tablets.get(to_text(tag))

        def require_tablet(self, tag):
            """Возвращает Tablet либо бросает TabletNotFound."""
            tag = to_text(tag)
            tablet = self._tablets.get(tag)
            if tablet is None:
                raise TabletNotFound("Tablet with tag '{}' is not registered".format(tag))
            return tablet

        def _generate_tag(self):
            chars = _string.ascii_uppercase + _string.digits

            while True:
                tag = "".join(
                    renpy.random.choice(chars)
                    for _ in range(4)
                )
                if tag not in self._tablets:
                    return tag

        def create_tablet(self, tag=None, charge=1000, max_charge=1000, discharge=1, register_in_cycle=True):
            if tag is None:
                tag = self._generate_tag()
            else:
                tag = to_text(tag)
                if tag in self._tablets:
                    raise FNaSRException("Tablet with tag '{}' already exists".format(tag))

            tablet = Tablet(
                tag,
                charge=charge,
                max_charge=max_charge,
                discharge=discharge,
            )
            self._tablets[tag] = tablet
            if register_in_cycle:
                require_system("cycle").register(tablet)
            return tablet

        def delete_tablet(self, tag):
            tablet = self.require_tablet(tag)

            if tablet._location_id is not None:
                self._detach_from_location(tablet)

            cycle = require_system("cycle")
            if cycle.is_registered(tablet):
                cycle.unregister(tablet)

            del self._tablets[tablet.tag]

        def move_tablet(self, tablet, new_location_id):
            """
            Перемещает планшет в новую локацию, поддерживая инварианты:
                * один Tablet -> максимум одна Location;
                * одна Location -> максимум один Tablet.

            Проверяет:
                * что tablet зарегистрирован именно в этом менеджере;
                * что целевая локация существует;
                * что целевая локация не занята другим планшетом.
            """
            if not isinstance(tablet, Tablet):
                raise FNaSRTypeError("tablet должен быть 'Tablet', получено '{}'".format(type(tablet)))

            if self._tablets.get(tablet.tag) is not tablet:
                raise TabletNotFound("Tablet with tag '{}' is not registered in this manager".format(tablet.tag))

            new_location_id = int(new_location_id)

            location_system = require_system("location")

            new_location = location_system.require_location(new_location_id)

            if new_location.tablet is not None and new_location.tablet is not tablet:
                raise FNaSRException("Location '{}' already holds tablet '{}'".format(new_location_id, new_location.tablet.tag))

            if tablet._location_id == new_location_id:
                return tablet

            self._detach_from_location(tablet)

            new_location._attach_tablet(tablet)
            tablet._location_id = new_location_id

            return tablet

        def unplace_tablet(self, tablet):
            """
            Убирает планшет из текущей Location, не удаляя его из системы
            (например, планшет "взяли в руки" и он временно нигде не лежит).
            """
            if not isinstance(tablet, Tablet):
                raise FNaSRTypeError("tablet должен быть 'Tablet', получено '{}'".format(type(tablet)))

            if self._tablets.get(tablet.tag) is not tablet:
                raise TabletNotFound("Tablet with tag '{}' is not registered in this manager".format(tablet.tag))

            self._detach_from_location(tablet)

        def _detach_from_location(self, tablet):
            """
            Внутренний хелпер: аккуратно снимает текущую физическую
            привязку планшета к Location (если она есть), синхронно
            обновляя обе стороны связи.
            """
            if tablet._location_id is None:
                return

            location_system = get_system("location")
            if location_system is not None:
                location = location_system.get_location(tablet._location_id)
                if location is not None and location.tablet is tablet:
                    location._detach_tablet()

            tablet._location_id = None

    register_system("tablet", TabletManager())

init python in v1FNaSR:
    def _v1_tablet_info_FNaSR(context):
        tablet = context.ps.current_player.current_location.tablet
        info = [
            "Заряд: {}".format(tablet.charge),
            "Проценты: {}".format(tablet.charge_percentage),
            "Хватит заряда: {}".format(tablet.get_formatted_time()),
            "Выбрано: {}".format(tablet.selected),
            "Камеры: {}".format(tablet.registered_locations),
        ]
        return "\n".join(info)

    _df = DebugIf(lambda context: context.ps.current_player.current_location.tablet is not None,
        DebugSection(
            DebugText(lambda context: "tablet: {}".format(context.ps.current_player.current_location.tablet.tag), order=0, style="v1_text_16_style_FNaSR"),
            DebugText(_v1_tablet_info_FNaSR, order=1),
        ),
        DebugText(lambda context: "Планшет отсутствует"), order=1)

    _df.context.ps = require_system("player")

    debug.add_element(_df, group="Location")

    del _v1_tablet_info_FNaSR
