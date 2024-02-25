import os
import queue
import threading
import cv2
import random
import time
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
import matplotlib.pyplot as plt

class Data:
    def __init__(self, delete_prev_data = True):
        self.data_path = './data.txt'
        self.data_queue = queue.Queue()
        if delete_prev_data:
            self.delete_data()
        self.thread = threading.Thread(target=self.write_to_file, name='Data')
        self.running = True
        self.thread.start()
        
    def write_to_file(self):
        while self.running:
            target = self.data_queue.get()
            if target is None:
                break
            with open(self.data_path, 'a') as f:
                f.write(f'{target[0]} {target[1]} {target[2]} {target[3]} {target[4]} {target[5]} {target[6]} {target[7]} {target[8]} {target[9]} {target[10]} {target[11]}\n')
    
    def delete_data(self):
        if Option_delete_prev_data:
            try:
                os.remove(self.data_path)
            except: pass
            try:
                os.remove('./mouse_net.pth')
            except: pass

    def add_target_data(self, target):
        self.data_queue.put(target)
        
    def stop(self):
        self.running = False
        self.data_queue.put(None)
        self.thread.join()

class Game_settings:
    def __init__(self):
        self.screen_width = Option_screen_width
        self.screen_height = Option_screen_height
        self.screen_x_center = int(self.screen_width / 2)
        self.screen_y_center = int(self.screen_height / 2)
        self.fov_x = Option_fov_x
        self.fov_y = Option_fov_y
        self.mouse_dpi = Option_mouse_dpi
        self.mouse_sensitivity = Option_mouse_sensitivity
    
    def randomize(self):
        screen_changed = False
        if Option_random_screen_resolution:
            self.screen_width = random.randint(Option_random_min_screen_resolution_width, Option_random_max_screen_resolution_width)
            self.screen_height = random.randint(Option_random_min_screen_resolution_height, Option_random_max_screen_resolution_height)
            screen_changed = True
            
        self.screen_x_center = int(self.screen_width / 2)
        self.screen_y_center = int(self.screen_height / 2)
        
        if Option_random_fov:
            self.fov_x = random.randint(Option_random_min_fov_x, Option_random_max_fov_x)
            self.fov_y = random.randint(Option_random_min_fov_y, Option_random_max_fov_y)
            
        if Option_random_mouse_dpi:
            self.mouse_dpi = random.randint(Option_random_min_mouse_dpi, Option_random_max_mouse_dpi)
            
        if Option_random_mouse_sensitivity:
            self.mouse_sensitivity = random.uniform(Option_random_min_mouse_sensitivity, Option_random_max_mouse_sensitivity)

        if screen_changed:
            target.randomize_position()
            target.randomize_size()
            target.randomize_velocity()
        
class Target:
    def __init__(self, x, y, w, h, dx, dy):
        w = min(w, game_settings.screen_width)
        h = min(h, game_settings.screen_height)
        
        self.x = x + w // 2
        self.y = y + h // 2
        self.w = w
        self.h = h
        self.dx = dx
        self.dy = dy
    
    def move(self):
        self.x += self.dx
        self.y += self.dy
        
        if self.x + self.w // 2 > game_settings.screen_width:
            self.x = game_settings.screen_width - self.w // 2
            self.dx = -self.dx
        
        if self.x - self.w // 2 < 0:
            self.x = self.w // 2
            self.dx = -self.dx
        
        if self.y + self.h // 2 > game_settings.screen_height:
            self.y = game_settings.screen_height - self.h // 2
            self.dy = -self.dy
        
        if self.y - self.h // 2 < 0:
            self.y = self.h // 2
            self.dy = -self.dy
            
    def randomize_position(self):
        max_x = game_settings.screen_width - self.w
        max_y = game_settings.screen_height - self.h
        
        self.x = random.uniform(self.w // 2, max_x + self.w // 2)
        self.y = random.uniform(self.h // 2, max_y + self.h // 2)
        
    def randomize_size(self):
        self.w = random.randint(Option_min_w, Option_max_w)
        self.h = random.randint(Option_min_h, Option_max_h)
        
    def randomize_velocity(self):
        self.dx += random.uniform(Option_gen_min_speed_x, Option_gen_max_speed_x)
        self.dy += random.uniform(Option_gen_min_speed_y, Option_gen_max_speed_y)

        self.dx = max(-1, min(self.dx, 1))
        self.dy = max(-1, min(self.dy, 1))
        
class Visualisation(threading.Thread):
    def __init__(self):
        super(Visualisation, self).__init__()
        self.queue = queue.Queue()
        self.cv2_window_name = 'train_mouse_net'
        self.running = True
        self.start()
    
    def run(self):
        cv2.namedWindow(self.cv2_window_name) 
        while self.running:
            image = np.zeros((game_settings.screen_height, game_settings.screen_width, 3), np.uint8)
            
            try:
                data = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if data is None:
                break
            
            if Option_gen_visualise_draw_line:
                cv2.line(image, (int(game_settings.screen_x_center), int(game_settings.screen_y_center)), (int(data.x), int(data.y)), (0, 255, 255), 2)
            
            cv2.rectangle(image, (int(data.x - data.w // 2), int(data.y - data.h // 2)), (int(data.x + data.w // 2), int(data.y + data.h // 2)), (0, 255, 0), 2)
            cv2.imshow(self.cv2_window_name, image)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    def stop(self):
        self.running = False
        self.queue.put(None)
        self.join()
            
def adjust_mouse_movement_proxy(target_x, target_y):
    offset_x = target_x - game_settings.screen_x_center
    offset_y = target_y - game_settings.screen_y_center

    degrees_per_pixel_x = game_settings.fov_x / game_settings.screen_width
    degrees_per_pixel_y = game_settings.fov_y / game_settings.screen_height
    
    mouse_move_x = offset_x * degrees_per_pixel_x

    mouse_dpi_move_x = (mouse_move_x / 360) * (game_settings.mouse_dpi * (1 / game_settings.mouse_sensitivity))

    mouse_move_y = offset_y * degrees_per_pixel_y
    mouse_dpi_move_y = (mouse_move_y / 360) * (game_settings.mouse_dpi * (1 / game_settings.mouse_sensitivity))

    return mouse_dpi_move_x, mouse_dpi_move_y
    
class CustomDataset(Dataset):
    def __init__(self, filepath):
        self.data = []
        with open(filepath, 'r') as f:
            for line in f:
                values = list(map(float, line.split()))
                self.data.append((values[:10], values[10:]))

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        inputs, targets = self.data[idx]
        return torch.tensor(inputs, dtype=torch.float32), torch.tensor(targets, dtype=torch.float32)

class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(10, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, 2)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = self.fc3(x)
        return x
    
def train_net():
    print(f'Starting train mouse_net model.\nUsing device: {device}.')
    dataset = CustomDataset(data.data_path)
    dataloader = DataLoader(dataset, batch_size=Option_batch_size, shuffle=True)
    model = SimpleNN().to(device)

    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    epochs = Option_train_epochs
    loss_values = []
    
    start_time = time.time()
    
    for epoch in range(epochs):
        epoch_losses = []
        for inputs, targets in dataloader:
            last_update_time = time.time()
            inputs, targets = inputs.to(device), targets.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            epoch_losses.append(loss.item())
        
        epoch_loss = np.mean(epoch_losses)
        loss_values.append(epoch_loss)
        
        train_time = last_update_time - start_time
        
        print(f'Epoch {epoch+1}/{epochs}', 'Loss: {:.5f}'.format(epoch_loss), 'Time: {:.2f} seconds'.format(train_time))
    
    plt.plot(loss_values)
    plt.title('Loss over epochs')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.get_current_fig_manager().set_window_title('Training complete')
    torch.save(model.state_dict(), 'mouse_net.pth')
    plt.show()

    
def test_model(input_data):
    model = SimpleNN().to(device)
    model.load_state_dict(torch.load('mouse_net.pth', map_location=device))
    model.eval()

    input_tensor = torch.tensor(input_data, dtype=torch.float32).to(device)

    with torch.no_grad():
        prediction = model(input_tensor)

    return prediction.cpu().numpy()

def read_random_line():
    with open(data.data_path, 'r') as file:
        lines = file.readlines()
        random_line = random.choice(lines).strip()
        return random_line

def convert_to_float_list(line):
    return [float(number) for number in line.split()]

def gen_data():
    global target
    target = Target(
        x=random.randint(0, game_settings.screen_width),
        y=random.randint(0, game_settings.screen_height),
        w=random.uniform(Option_min_w, Option_max_w),
        h=random.uniform(Option_min_h, Option_max_h),
        dx=random.uniform(Option_gen_min_speed_x, Option_gen_max_speed_x),
        dy=random.uniform(Option_gen_min_speed_y, Option_gen_max_speed_y))

    start_time = time.time()
    last_update_time = time.time()
    
    pbar = tqdm(total=Option_gen_time, desc='Data generation')
    while True:
        current_time = time.time()

        if current_time - last_update_time > 1:
            last_update_time = current_time

        target.move()
        target.randomize_position()
        target.randomize_size()
        target.randomize_velocity()
        game_settings.randomize()
        
        
        if Option_gen_visualise:
            vision.queue.put(target)
        
        move_proxy = adjust_mouse_movement_proxy(target_x=target.x, target_y=target.y)
        
        data.add_target_data((game_settings.screen_width,
                                game_settings.screen_height,
                                game_settings.screen_x_center,
                                game_settings.screen_y_center,
                                game_settings.mouse_dpi,
                                game_settings.mouse_sensitivity,
                                game_settings.fov_x,
                                game_settings.fov_y,
                                target.x,
                                target.y,
                                move_proxy[0],
                                move_proxy[1]))
        
        pbar.n = int(last_update_time - start_time)
        pbar.refresh()

        if int(last_update_time - start_time) >= Option_gen_time:
            if Option_gen_visualise:
                vision.queue.put(None)
            data.stop()
            pbar.close()
            break
        
if __name__ == "__main__":
    ###################### Options ######################
    
    # Data
    Option_delete_prev_data = True
    
    # Train
    Option_train = True
    Option_train_epochs = 20
    Option_batch_size = 64
    
    # Testing model
    Option_test_model = True
    
    # Generation settings
    Option_Generation = True
    Option_gen_time = 180
    
    Option_gen_visualise = False
    Option_gen_visualise_draw_line = False
    
    # Scale
    Option_min_w = 5
    Option_max_w = 500
    Option_min_h = 5
    Option_max_h = 500
    
    # Speed - 1 is max
    Option_gen_min_speed_x = -1
    Option_gen_max_speed_x = 1
    Option_gen_min_speed_y = -1
    Option_gen_max_speed_y = 1
    
    # Game settings (The data was copied from this config https://github.com/SunOner/yolov8_aimbot/blob/main/config.ini)
    Option_screen_width = 384
    Option_screen_height = 216
    Option_fov_x = 90
    Option_fov_y = 55
    Option_mouse_dpi = 1000
    Option_mouse_sensitivity = 1
    
    # Game settings - random options
    Option_random_screen_resolution = True
    Option_random_min_screen_resolution_width = 300
    Option_random_max_screen_resolution_width = 500
    Option_random_min_screen_resolution_height = 150
    Option_random_max_screen_resolution_height = 500
    
    Option_random_fov = True
    Option_random_min_fov_x = 80
    Option_random_max_fov_x = 100
    Option_random_min_fov_y = 45
    Option_random_max_fov_y = 70
    
    Option_random_mouse_dpi = True
    Option_random_min_mouse_dpi = 1000
    Option_random_max_mouse_dpi = 2000
    
    Option_random_mouse_sensitivity = True
    Option_random_min_mouse_sensitivity = 1
    Option_random_max_mouse_sensitivity = 3

    #####################################################

    game_settings = Game_settings()
    
    
    data = Data(delete_prev_data=Option_delete_prev_data)
    
    if Option_gen_visualise:
        vision = Visualisation()
    
    if Option_train or Option_test_model:
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    
    if Option_Generation:
        gen_data()
        
    if Option_gen_visualise:
        vision.stop()
    
    if Option_train:
        train_net()

    if Option_test_model:
        random_line = read_random_line()
        data_list = convert_to_float_list(random_line)
        input_data = data_list[:10]
        output = test_model(input_data)
        print(f'Tested model:\nCalculated: {str(adjust_mouse_movement_proxy(data_list[8], data_list[9]))}\nModel output: {output}')
        data.stop()