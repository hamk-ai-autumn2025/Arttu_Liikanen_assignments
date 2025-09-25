import random
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCORE_FILE = os.path.join(BASE_DIR, "highscores.txt")

def load_scores():
    """Load high scores from file into a dictionary."""
    scores = {}
    if os.path.exists(SCORE_FILE):
        with open(SCORE_FILE, "r", encoding="utf-8") as f:  # <-- add encoding
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == 2:
                    name, score = parts
                    try:
                        scores[name] = int(score)
                    except ValueError:
                        continue
    return scores

def save_scores(scores):
    """Save high scores to file with UTF-8 encoding."""
    with open(SCORE_FILE, "w", encoding="utf-8") as f:  # <-- add encoding
        for name, score in scores.items():
            f.write(f"{name}|{score}\n")



def choose_difficulty():
    """Let the player select a difficulty level."""
    print("\nSelect Difficulty:")
    print("1. Easy (1–10)")
    print("2. Medium (1–50)")
    print("3. Hard (1–100)")
    print("4. Insane (1–500)")
    choice = input("Enter choice: ")

    if choice == "1":
        return 10
    elif choice == "2":
        return 50
    elif choice == "3":
        return 100
    elif choice == "4":
        return 500
    else:
        print("Invalid choice, defaulting to Easy.")
        return 10

def play_game(scores):
    """Play one round of the guessing game."""
    name = input("Enter your name: ")
    upper_limit = choose_difficulty()
    secret = random.randint(1, upper_limit)
    attempts = 0

    print(f"\nI’m thinking of a number between 1 and {upper_limit}. Can you guess it?")

    while True:
        try:
            guess = int(input("Your guess: "))
            attempts += 1
            if guess < secret:
                print("Too low!")
            elif guess > secret:
                print("Too high!")
            else:
                print(f"Correct! You guessed it in {attempts} tries.")
                break
        except ValueError:
            print("Please enter a valid number.")

    # Update high scores
    if name not in scores or attempts < scores[name]:
        scores[name] = attempts
        print("New personal best!")
    else:
        print(f"Your best score is still {scores[name]} attempts.")

def show_scores(scores):
    """Display all high scores sorted by attempts."""
    if not scores:
        print("No high scores yet. Be the first!")
        return
    print("\n=== High Scores ===")
    for name, score in sorted(scores.items(), key=lambda x: x[1]):
        print(f"{name}: {score} attempts")
    print("===================")

def main_menu():
    """Main menu loop for the game."""
    scores = load_scores()
    while True:
        print("\n--- Guess the Number ---")
        print("1. Play Game")
        print("2. View High Scores")
        print("3. Quit")
        choice = input("Choose an option: ")

        if choice == "1":
            play_game(scores)
        elif choice == "2":
            show_scores(scores)
        elif choice == "3":
            save_scores(scores)
            print("Thanks for playing! Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main_menu()
