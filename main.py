import os
import requests
import csv
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
from PIL import Image, ImageTk
from io import BytesIO

TMDB_API_KEY = ''


def get_tmdb_id(folder_name):
    results = []
    for search_type in ["tv", "movie"]:
        url = f'https://api.themoviedb.org/3/search/{search_type}?api_key={TMDB_API_KEY}&query={folder_name}'
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            results.extend(data['results'])
    return results if results else None


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
        self.image_cache = {}
        self.create_widgets()

    def create_widgets(self):
        self.root.geometry("600x600")
        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.folder_label = tk.Label(self.root, text="", font=('Arial', 14, 'bold'), wraplength=500, justify="center")
        self.folder_label.grid(row=0, column=0, pady=5, padx=5, sticky='ew')

        self.label = tk.Label(self.root, text="Select the correct TMDB ID:", font=('Arial', 14))
        self.label.grid(row=1, column=0, pady=5, padx=5, sticky='ew')

        self.tree = ttk.Treeview(self.root, columns=("Thumbnail", "Name"), show="tree")
        self.tree.grid(row=2, column=0, pady=5, padx=5, sticky='nsew')
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        style = ttk.Style()
        style.configure("Treeview", rowheight=80)

        self.spinner = tk.Label(self.root, text="Loading...", font=('Arial', 14), fg="blue")
        self.spinner.grid(row=3, column=0, pady=5, padx=5, sticky='ew')

        self.button_frame = tk.Frame(self.root)
        self.button_frame.grid(row=4, column=0, pady=5, padx=5, sticky='ew')

        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)
        self.button_frame.grid_columnconfigure(2, weight=1)
        self.button_frame.grid_columnconfigure(3, weight=1)

        self.selection_button = tk.Button(self.button_frame, text="Make Selection", command=self.make_selection, font=('Arial', 12))
        self.selection_button.grid(row=0, column=0, padx=5, sticky='ew')

        self.process_button = tk.Button(self.button_frame, text="Mark as Processed", command=self.mark_processed, font=('Arial', 12))
        self.process_button.grid(row=0, column=1, padx=5, sticky='ew')

        self.skip_button = tk.Button(self.button_frame, text="Skip", command=self.skip, font=('Arial', 12))
        self.skip_button.grid(row=0, column=2, padx=5, sticky='ew')

        self.manual_search_button = tk.Button(self.button_frame, text="Manual Search", command=self.manual_search, font=('Arial', 12))
        self.manual_search_button.grid(row=0, column=3, padx=5, sticky='ew')

        self.spinner.grid_remove()
        self.next_folder()

    def on_select(self, event):
        pass

    def next_folder(self):
        if not self.folder_paths:
            messagebox.showinfo("Completed", "All folders have been processed.")
            self.root.quit()
            return
        self.current_folder = self.folder_paths.pop(0)
        self.folder_label.config(text=f"Currently Processing: {os.path.basename(self.current_folder)}")
        if os.path.isdir(self.current_folder):
            folder_name = os.path.basename(self.current_folder)
            self.start_loading()
            self.tmdb_results = get_tmdb_id(folder_name)
            self.stop_loading()
            self.populate_tree()

    def populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        if self.tmdb_results:
            max_name_length = 0
            for result in self.tmdb_results:
                name = result.get('name', result.get('title', 'Unknown Title'))
                description = result.get('overview', 'No description available.')
                display_text = f"{name} ({result['id']})\n{description}"

                max_name_length = max(max_name_length, len(name))

                if 'poster_path' in result and result['poster_path']:
                    img_url = f"https://image.tmdb.org/t/p/w500{result['poster_path']}"
                    response = requests.get(img_url)
                    img_data = response.content
                    img = Image.open(BytesIO(img_data))
                    img = img.resize((50, 75), Image.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)
                    self.image_cache[result['id']] = img_tk  # Cache the image
                    self.tree.insert("", "end", iid=result['id'], text=display_text, image=img_tk)
                else:
                    self.tree.insert("", "end", iid=result['id'], text=display_text)
            self.tree.column("#0", width=max_name_length * 10)
        else:
            self.handle_error(os.path.basename(self.current_folder))

    def handle_error(self, folder_name):
        response = messagebox.askquestion(
            "No Results Found",
            f"No TMDB ID found for '{folder_name}'. Would you like to perform a manual search or skip?",
            icon="warning"
        )
        if response == "yes":
            self.manual_search()
        else:
            self.skip()

    def start_loading(self):
        self.spinner.grid()
        self.root.update_idletasks()

    def stop_loading(self):
        self.spinner.grid_remove()

    def manual_search(self):
        search_query = simpledialog.askstring("Manual Search", "Enter the name to search:")
        if search_query:
            self.start_loading()
            self.tmdb_results = get_tmdb_id(search_query)
            self.stop_loading()
            self.populate_tree()

    def make_selection(self):
        selection = self.tree.selection()
        if selection:
            item_id = selection[0]
            for result in self.tmdb_results:
                if result['id'] == int(item_id):
                    tmdb_id = result['id']
                    new_name = result.get('name', result.get('title'))
                    release_year = result.get('first_air_date', result.get('release_date', 'Unknown'))[:4]
                    new_folder_path = rename_folder_with_tmdb_id(self.current_folder, new_name, release_year, tmdb_id)
                    mark_as_processed(self.processed_file, new_folder_path)
                    print(f"Folder renamed to: {new_folder_path}")
                    break
            self.tree.selection_remove(item_id)
            self.next_folder()

    def mark_processed(self):
        if self.current_folder:
            mark_as_processed(self.processed_file, self.current_folder)
        self.next_folder()

    def skip(self):
        self.next_folder()


def select_folders():
    FOLDER_PATHS = [
        "D:/Media/Shows",
        "D:/Media/Movies",
        "E:/Media/Shows",
        "F:/Media/Movies"
    ]
    processed_file = 'already_processed.csv'
    processed_folders = set()

    if os.path.isfile(processed_file):
        with open(processed_file, mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    processed_folders.add(row[0])

    folder_paths = []
    for folder_path in FOLDER_PATHS:
        if os.path.isdir(folder_path):
            for subfolder in os.listdir(folder_path):
                subfolder_path = os.path.join(folder_path, subfolder)
                if os.path.isdir(subfolder_path) and subfolder_path not in processed_folders:
                    print(f"Adding folder for processing: {subfolder_path}")
                    folder_paths.append(subfolder_path)

    return folder_paths, processed_file


if __name__ == "__main__":
    root = tk.Tk()
    root.title("TMDB Folder Processor")
    folder_paths, processed_file = select_folders()
    app = TMDBApp(root, folder_paths, processed_file)
    root.mainloop()
