from .enums import GenderEnum

class Player:
    def __init__(self, name: str, district: int, gender: GenderEnum = GenderEnum.OTHER):
        self.name: str = name
        self.district: int = district
        self.genderEnum: GenderEnum = gender;
        self.genderRef: str = gender.value
        self.alive: bool = True
        self.kills: int = 0
        self.cause_of_death: str = ""

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.name == other.name and self.district == other.district and self.genderRef == other.genderRef
        return False

    def __ne__(self, other):
        return self.name != other.name or self.district != other.district or self.genderRef != other.genderRef

    def __lt__(self, other):
        return (self.district, self.genderRef, self.name) < (other.district, other.genderRef, other.name)

    def __le__(self, other):
        return (self.district, self.genderRef, self.name) <= (other.district, other.genderRef, other.name)

    def __gt__(self, other):
        return (self.district, self.genderRef, self.name) > (other.district, other.genderRef, other.name)

    def __ge__(self, other):
        return (self.district, self.genderRef, self.name) >= (other.district, other.genderRef, other.name)

    def __hash__(self):
        return hash((self.district, self.genderRef, self.name))

    @property
    def pronoun(self):
        return self.genderRef

    @property
    def pronounCap(self):
        return self.genderRef.capitalize()

    @property
    def pronounRef(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "him"
        elif (self.genderRef == "she"):
            ref = "her"
        else:
            ref = "them"
        return ref

    @property
    def pronounRefCap(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "him"
        elif (self.genderRef == "she"):
            ref = "her"
        else:
            ref = "them"
        return ref.capitalize()

    @property
    def pronounSelf(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "himself"
        elif (self.genderRef == "she"):
            ref = "herself"
        else:
            ref = "themself"
        return ref

    @property
    def pronounSelfCap(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "himself"
        elif (self.genderRef == "she"):
            ref = "herself"
        else:
            ref = "themself"
        return ref.capitalize()

    @property
    def pronounOwn(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "his"
        elif (self.genderRef == "she"):
            ref = "her"
        else:
            ref = "their"
        return ref

    @property
    def pronounOwnCap(self):
        ref: str = None
        if(self.genderRef == "he"):
            ref = "his"
        elif (self.genderRef == "she"):
            ref = "her"
        else:
            ref = "their"
        return ref.capitalize()