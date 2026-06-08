from turtle import Screen
from Snake import Snake
from food import Food
from scoreboard import Scoreboard
import time

SCREEN_SIZE = 600
BOUNDARY = 290
BASE_SPEED = 0.15
MIN_SPEED = 0.05

screen = Screen()
screen.setup(width=SCREEN_SIZE, height=SCREEN_SIZE)
screen.bgcolor("black")
screen.title("Snake Game")
screen.tracer(0)

snake = Snake()
food = Food()
scoreboard = Scoreboard()

game_active = False
game_over_shown = False

def start_game():
    global game_active, game_over_shown
    if not game_active:
        snake.reset()
        scoreboard.reset()
        scoreboard.clear()
        scoreboard.update_score()
        food.refresh()
        game_active = True
        game_over_shown = False
        run_game()

def run_game():
    global game_active, game_over_shown

    while game_active:
        speed = max(MIN_SPEED, BASE_SPEED - (scoreboard.score // 50) * 0.01)
        time.sleep(speed)
        screen.update()
        snake.move()

        if snake.head.distance(food) < 15:
            food.refresh()
            snake.extend()
            scoreboard.increase_score()

        head_x = snake.head.xcor()
        head_y = snake.head.ycor()

        if head_x > BOUNDARY or head_x < -BOUNDARY or head_y > BOUNDARY or head_y < -BOUNDARY:
            game_active = False
            scoreboard.game_over()
            screen.update()

        for segment in snake.segments[1:]:
            if snake.head.distance(segment) < 10:
                game_active = False
                scoreboard.game_over()
                screen.update()

screen.listen()
screen.onkeypress(key="Up", fun=snake.up)
screen.onkeypress(key="Down", fun=snake.down)
screen.onkeypress(key="Right", fun=snake.right)
screen.onkeypress(key="Left", fun=snake.left)
screen.onkeypress(key="w", fun=snake.up)
screen.onkeypress(key="s", fun=snake.down)
screen.onkeypress(key="d", fun=snake.right)
screen.onkeypress(key="a", fun=snake.left)
screen.onkeypress(key="space", fun=start_game)

scoreboard.goto(0, 0)
scoreboard.write("Press SPACE to start", align="center", font=("Courier", 18, "bold"))
screen.update()

screen.exitonclick()