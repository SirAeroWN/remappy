class Layer():
    def __init__(self, min_layer, max_layer, default_layer=0):
        self.min = min_layer
        self.max = max_layer
        self.layer = default_layer

    def inc(self, scalar):
        self.layer = min(self.max, self.layer + scalar)

    def dec(self, scalar):
        self.layer = max(self.min, self.layer - scalar)

    def _next(self, arr):
        for i, lyr in enumerate(arr):
            if lyr == self.layer:
                return (i + 1) % len(arr)
        else:
            return 0

    def rotate(self, arr):
        self.layer = arr[self._next(arr)]
        print(self.layer)

    def set(self, constant):
        if min(self.max, constant) == max(self.min, constant):
            self.layer = constant
