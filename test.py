import random
import string

def random_sig():
    # Generate 3 random characters (could be letters or digits)
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(3))

# Example usage:
print(random_sig())
