class FoxType(type):
    """
    Custom metaclass:
        1. Implement a singleton
        2. Automatically run the __auto_run__ method (if the instance has this method)

    The metaclass produces the execution logic of the class object:
        1. Automatically call __new__ of the metaclass itself to create an empty class object
        2. Automatically call __init__ of the metaclass itself to fill in data for empty class objects

    Metaclass __call__ executes logic on instantiated objects of class objects:
        1. Call the class object's own __new__ to create an empty instance object
        2. Call the __init__ of the class object itself to fill in the data for the empty instance object
        3. Return the created instance object
    """

    def _create_instance(cls, *args, **kwargs):
        obj = cls.__new__(cls, *args, **kwargs)  # type: ignore
        cls.__init__(obj, *args, **kwargs)
        return obj

    def __call__(cls, *args, **kwargs):
        instance = "instance"
        method_name = "__auto_run__"
        sigleton = getattr(cls, "_SINGLETON", False)
        instance_object = None

        if sigleton:
            if not hasattr(cls, instance):
                setattr(cls, instance, cls._create_instance(*args, **kwargs))
            instance_object = getattr(cls, instance)
        else:
            instance_object = cls._create_instance(*args, **kwargs)

        if hasattr(instance_object, method_name):
            getattr(instance_object, method_name)()

        return instance_object
