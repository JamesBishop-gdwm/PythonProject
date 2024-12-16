import os
import requests
import csv
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from PIL import Image, ImageTk
from io import BytesIO

TMDB_API_KEY = 'f0f356f9c383dc1097b9035f2431f4d0'  # Replace with your TMDB API key

def get_tmdb_id(folder_name):
    url = f'https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={folder_name}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data['results']
    return None

def sanitize_folder_name(name):
    # Remove illegal characters for Windows file names
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in illegal_chars:
        name = name.replace(char, '')
    return name

def rename_folder_with_tmdb_id(folder_path, new_name, release_year, tmdb_id):
    base_folder = os.path.dirname(folder_path)
    new_folder_name = sanitize_folder_name(f"{new_name} ({release_year}) [tmdbid-{tmdb_id}]")
    new_folder_path = os.path.join(base_folder, new_folder_name)
    os.rename(folder_path, new_folder_path)
    return new_folder_path

def mark_as_processed(file_path, folder_path):
    with open(file_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([folder_path])

class TMDBApp:
    def __init__(self, root, folder_paths, processed_file):
        self.root = root
        self.folder_paths = folder_paths
        self.processed_file = processed_file
        self.current_folder = None
        self.tmdb_results = None
        self.image_cache = {}  # Cache to store thumbnails
        self.create_widgets()

    def create_widgets(self):
        self.root.geometry("600x600")

        self.folder_label = tk.Label(self.root, text="", font=('Arial', 14, 'bold'))
        self.folder_label.pack(pady=10)

        self.label = tk.Label(self.root, text="Select the correct TMDB ID:", font=('Arial', 14))
        self.label.pack(pady=10)

        self.tree = ttk.Treeview(self.root, columns=("Thumbnail", "Name"), show="tree")
        self.tree.pack(pady=10, fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        self.selection_button = tk.Button(self.root, text="Make Selection", command=self.make_selection, font=('Arial', 12))
        self.selection_button.pack(pady=5)

        self.process_button = tk.Button(self.root, text="Mark as Processed", command=self.mark_processed, font=('Arial', 12))
        self.process_button.pack(pady=5)

        self.skip_button = tk.Button(self.root, text="Skip", command=self.skip, font=('Arial', 12))
        self.skip_button.pack(pady=5)

        self.manual_search_button = tk.Button(self.root, text="Manual Search", command=self.manual_search, font=('Arial', 12))
        self.manual_search_button.pack(pady=5)

        self.next_folder()

    def on_select(self, event):
        pass  # No need to handle selection for now

    def next_folder(self):
        if not self.folder_paths:
            messagebox.showinfo("Completed", "All folders have been processed.")
            self.root.quit()
            return
        self.current_folder = self.folder_paths.pop(0)
        self.folder_label.config(text=f"Currently Processing: {os.path.basename(self.current_folder)}")
        if os.path.isdir(self.current_folder):
            folder_name = os.path.basename(self.current_folder)
            self.tmdb_results = get_tmdb_id(folder_name)
            self.tree.delete(*self.tree.get_children())  # Clear the treeview
            if self.tmdb_results:
                for result in self.tmdb_results:
                    display_text = f"{result['name']} ({result['id']})"
                    if 'poster_path' in result and result['poster_path']:
                        img_url = f"https://image.tmdb.org/t/p/w500{result['poster_path']}"
                        response = requests.get(img_url)
                        img_data = response.content
                        img = Image.open(BytesIO(img_data))
                        img = img.resize((50, 75), Image.LANCZOS)  # Resize for thumbnail
                        img_tk = ImageTk.PhotoImage(img)
                        self.image_cache[result['id']] = img_tk  # Cache the image
                        self.tree.insert("", "end", iid=result['id'], text=display_text, image=img_tk)
                    else:
                        self.tree.insert("", "end", iid=result['id'], text=display_text)

    def manual_search(self):
        search_query = simpledialog.askstring("Manual Search", "Enter the name to search:")
        if search_query:
            self.tmdb_results = get_tmdb_id(search_query)
            self.tree.delete(*self.tree.get_children())  # Clear the treeview
            if self.tmdb_results:
                for result in self.tmdb_results:
                    display_text = f"{result['name']} ({result['id']})"
                    if 'poster_path' in result and result['poster_path']:
                        img_url = f"https://image.tmdb.org/t/p/w500{result['poster_path']}"
                        response = requests.get(img_url)
                        img_data = response.content
                        img = Image.open(BytesIO(img_data))
                        img = img.resize((50, 75), Image.LANCZOS)  # Resize for thumbnail
                        img_tk = ImageTk.PhotoImage(img)
                        self.image_cache[result['id']] = img_tk  # Cache the image
                        self.tree.insert("", "end", iid=result['id'], text=display_text, image=img_tk)
                    else:
                        self.tree.insert("", "end", iid=result['id'], text=display_text)
            else:
                messagebox.showerror("Error", f"No TMDB ID found for '{search_query}'")

    def make_selection(self):
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            for result in self.tmdb_results:
                if result['id'] == int(item_id):
                    tmdb_id = result['id']
                    new_name = result['name']
                    release_year = result.get('first_air_date', 'Unknown')[:4] if 'first_air_date' in result else 'Unknown'
                    new_folder_path = rename_folder_with_tmdb_id(self.current_folder, new_name, release_year, tmdb_id)
                    mark_as_processed(self.processed_file, new_folder_path)
                    messagebox.showinfo("Success", f"Folder renamed to: {new_folder_path}")
                    break
            self.tree.selection_remove(item_id)  # Clear selection after making a selection
            self.next_folder()

    def mark_processed(self):
        self.next_folder()

    def skip(self):
        self.next_folder()

def select_folders():
    FOLDER_PATHS = [
        "D:/Media/Shows",  # Example folder paths, add more as needed
        "D:/Media/Movies"
    ]
    processed_file = 'already_processed.csv'
    folder_paths = []
    for folder_path in FOLDER_PATHS:
        if os.path.isdir(folder_path):
            for subfolder in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder)
                if os.path.isdir(subfolder_path):
                    print(f"Adding folder for processing: {subfolder_path}")
                    folder_paths.append(subfolder_path)
    return folder_paths, processed_file

if __name__ == "__main__":
    root = tk.Tk()
    root.title("TMDB Folder Processor")
    folder_paths, processed_file = select_folders()
    app = TMDBApp(root, folder_paths, processed_file)
    root.mainloop()