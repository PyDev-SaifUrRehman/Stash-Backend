import random
import string

def generate_referral_code():
    part1 = ''.join(random.choices(string.digits, k=2)) + ''.join(random.choices(string.ascii_uppercase, k=2))    
    part2 = random.choice(string.ascii_uppercase) + ''.join(random.choices(string.digits, k=2))
    random_string = f"{part1}-{part2}"
    return random_string

