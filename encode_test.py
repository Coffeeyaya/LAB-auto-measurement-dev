def check_binary_balance(message):
    # Convert message to binary string
    binary_string = "".join([format(ord(c), '08b') for c in message])
    
    total_bits = len(binary_string)
    ones = binary_string.count('1')
    zeros = binary_string.count('0')
    
    print(f"Message Length: {len(message)} characters")
    print(f"Total Bits:     {total_bits}")
    print("-" * 25)
    print(f"Total '1's:     {ones} ({ones/total_bits:.1%})")
    print(f"Total '0's:     {zeros} ({zeros/total_bits:.1%})")

# Test your own message here!
my_message = "My motivation runs, but I prefer walking."
check_binary_balance(my_message)