from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
import psycopg2
import pandas as pd
from datetime import datetime



    

# Set window size and color
Window.size = (800, 600)
Window.clearcolor = get_color_from_hex('#f0f0f0')

# Custom styles
COLORS = {
    'primary': '#2196F3',    # Blue
    'secondary': '#4CAF50',  # Green
    'danger': '#F44336',     # Red
    'text': '#212121',       # Dark Gray
    'background': '#FFFFFF', # White
}

class StyledLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color = get_color_from_hex(COLORS['text'])
        self.font_size = '16sp'
        self.bold = True

class StyledButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = get_color_from_hex(COLORS['primary'])
        self.color = get_color_from_hex('#FFFFFF')
        self.size_hint_y = None
        self.height = 50
        self.font_size = '16sp'

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = get_color_from_hex('#FFFFFF')
        self.foreground_color = get_color_from_hex(COLORS['text'])
        self.cursor_color = get_color_from_hex(COLORS['primary'])
        self.font_size = '16sp'
        self.padding = [10, 10]
        self.size_hint_y = None
        self.height = 40

class StyledSpinner(Spinner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = get_color_from_hex('#FFFFFF')
        self.color = get_color_from_hex(COLORS['text'])
        self.size_hint_y = None
        self.height = 40
        self.font_size = '16sp'


class DatabaseManager:
    def __init__(self):
        self.conn = psycopg2.connect(
            database="perpustakaan",
            user="postgres",
            password="13012005",
            host="localhost",
            port="5432"
        )
        self.cur = self.conn.cursor()

    def get_available_books(self):
        self.cur.execute("SELECT id_buku, judul FROM buku WHERE stok > 0")
        return self.cur.fetchall()
    
    def get_all_members(self):
        self.cur.execute("SELECT id_anggota, nama FROM anggota")
        return self.cur.fetchall()
    
    def add_member(self, nama, alamat, telepon, email):
        try:
            self.cur.execute("""
                INSERT INTO anggota (nama, alamat, no_telepon, email)
                VALUES (%s, %s, %s, %s)
                RETURNING id_anggota
            """, (nama, alamat, telepon, email))
            member_id = self.cur.fetchone()[0]
            self.conn.commit()
            return member_id
        except Exception as e:
            self.conn.rollback()
            raise e

    def create_loan(self, book_id, member_id):
        try:
            # Check book availability
            self.cur.execute("SELECT stok FROM buku WHERE id_buku = %s", (book_id,))
            stock = self.cur.fetchone()[0]
            
            if stock > 0:
                # Create loan record
                self.cur.execute("""
                    INSERT INTO peminjaman (id_buku, id_anggota, tanggal_pinjam, tanggal_kembali, status)
                    VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE + INTERVAL '14 days', 'Dipinjam')
                    RETURNING id_peminjaman
                """, (book_id, member_id))
                
                # Update book stock
                self.cur.execute("""
                    UPDATE buku SET stok = stok - 1
                    WHERE id_buku = %s
                """, (book_id,))
                
                self.conn.commit()
                return True, "Peminjaman berhasil!"
            else:
                return False, "Buku tidak tersedia!"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"
    
    def return_book(self, loan_id):
        try:
            # Get book ID from the loan
            self.cur.execute("SELECT id_buku FROM peminjaman WHERE id_peminjaman = %s", (loan_id,))
            book_id = self.cur.fetchone()[0]

            # Update loan status
            self.cur.execute("""
                UPDATE peminjaman
                SET status = 'Dikembalikan', tanggal_kembali = CURRENT_DATE
                WHERE id_peminjaman = %s
            """, (loan_id,))

            # Increase book stock
            self.cur.execute("""
                UPDATE buku SET stok = stok + 1
                WHERE id_buku = %s
            """, (book_id,))

            self.conn.commit()
            return True, "Buku berhasil dikembalikan!"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"

    def get_active_loans(self):
        self.cur.execute("""
            SELECT p.id_peminjaman, b.judul, a.nama
            FROM peminjaman p
            JOIN buku b ON p.id_buku = b.id_buku
            JOIN anggota a ON p.id_anggota = a.id_anggota
            WHERE p.status = 'Dipinjam'
        """)
        return self.cur.fetchall()
    
    # def delete_member(self, member_id):
    #     try:
    #         # Check if member has active loans
    #         self.cur.execute("""
    #             SELECT COUNT(*) FROM peminjaman 
    #             WHERE id_anggota = %s AND status = 'Dipinjam'
    #         """, (member_id,))
    #         active_loans = self.cur.fetchone()[0]
            
    #         if active_loans > 0:
    #             return False, "Anggota masih memiliki peminjaman aktif!"
            
    #         # Delete member
    #         self.cur.execute("DELETE FROM anggota WHERE id_anggota = %s", (member_id,))
    #         self.conn.commit()
    #         return True, "Anggota berhasil dihapus!"
    #     except Exception as e:
    #         self.conn.rollback()
    #         return False, f"Error: {str(e)}"

    def delete_member(self, member_id):
        try:
            # Check if member has any loans (active or returned)
            self.cur.execute("""
                SELECT COUNT(*) FROM peminjaman 
                WHERE id_anggota = %s
            """, (member_id,))
            total_loans = self.cur.fetchone()[0]
            
            if total_loans > 0:
                # Check if all loans are returned
                self.cur.execute("""
                    SELECT COUNT(*) FROM peminjaman 
                    WHERE id_anggota = %s AND status = 'Dipinjam'
                """, (member_id,))
                active_loans = self.cur.fetchone()[0]
                
                if active_loans > 0:
                    return False, "Anggota masih memiliki peminjaman aktif!"
            
            # Delete member
            self.cur.execute("DELETE FROM anggota WHERE id_anggota = %s", (member_id,))
            self.conn.commit()
            return True, "Anggota berhasil dihapus!"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error: {str(e)}"

class PeminjamanScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        
        # Main layout with padding and white background
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        main_layout.background_color = get_color_from_hex(COLORS['background'])
        
        # Header
        header = StyledLabel(
            text='Form Peminjaman Buku',
            font_size='24sp',
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(header)
        
        # Form Layout
        form = GridLayout(cols=2, spacing=15, size_hint_y=None, height=300)
        
        # Member Input Fields
        form.add_widget(StyledLabel(text='Nama:'))
        self.input_nama = StyledTextInput(multiline=False)
        form.add_widget(self.input_nama)
        
        form.add_widget(StyledLabel(text='Alamat:'))
        self.input_alamat = StyledTextInput(multiline=False)
        form.add_widget(self.input_alamat)
        
        form.add_widget(StyledLabel(text='No. Telepon:'))
        self.input_telepon = StyledTextInput(multiline=False)
        form.add_widget(self.input_telepon)

        form.add_widget(StyledLabel(text='Email:'))
        self.input_email = StyledTextInput(multiline=False)
        form.add_widget(self.input_email)
        
        form.add_widget(StyledLabel(text='Pilih Buku:'))
        books = self.db.get_available_books()
        book_list = [f"{id} - {title}" for id, title in books]
        self.book_spinner = StyledSpinner(text='Pilih Buku', values=book_list)
        form.add_widget(self.book_spinner)
        
        main_layout.add_widget(form)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=20)
        
        btn_submit = StyledButton(
            text='Proses Peminjaman',
            on_press=self.process_loan,
            background_color=get_color_from_hex(COLORS['secondary'])
        )
        btn_back = StyledButton(
            text='Kembali',
            on_press=self.back_to_main,
            background_color=get_color_from_hex(COLORS['danger'])
        )
        
        button_layout.add_widget(btn_submit)
        button_layout.add_widget(btn_back)
        main_layout.add_widget(button_layout)
        
        # Status Label
        self.status_label = StyledLabel(
            text='',
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(self.status_label)
        
        self.add_widget(main_layout)

    def validate_input(self):
        if not self.input_nama.text:
            return False, "Nama harus diisi!"
        if not self.input_alamat.text:
            return False, "Alamat harus diisi!"
        if not self.input_telepon.text:
            return False, "No. Telepon harus diisi!"
        if not self.input_email.text:
            return False, "Email harus diisi!"
        if self.book_spinner.text == 'Pilih Buku':
            return False, "Silakan pilih buku!"
        return True, ""
    
    def process_loan(self, instance):
        # Validate input
        is_valid, message = self.validate_input()
        if not is_valid:
            self.status_label.text = message
            return
        
        try:
            # Add new member
            member_id = self.db.add_member(
                self.input_nama.text,
                self.input_alamat.text,
                self.input_telepon.text,
                self.input_email.text
            )
            
            # Process loan
            book_id = int(self.book_spinner.text.split(' - ')[0])
            success, message = self.db.create_loan(book_id, member_id)
            
            if success:
                # Clear inputs
                self.input_nama.text = ''
                self.input_alamat.text = ''
                self.input_telepon.text = ''
                self.input_email.text = ''
                self.book_spinner.text = 'Pilih Buku'
                
                # Refresh book list
                books = self.db.get_available_books()
                self.book_spinner.values = [f"{id} - {title}" for id, title in books]
            
            self.status_label.text = message
            
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"

    def back_to_main(self, instance):
        self.manager.current = 'main'

class PengembalianScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        header = StyledLabel(
            text='Pengembalian Buku',
            font_size='24sp',
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(header)
        
        # Loan Selection
        self.loan_spinner = StyledSpinner(
            text='Pilih Peminjaman',
            size_hint_y=None,
            height=40
        )
        self.load_active_loans()
        main_layout.add_widget(self.loan_spinner)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=20)
        btn_return = StyledButton(
            text='Kembalikan Buku',
            on_press=self.return_book,
            background_color=get_color_from_hex(COLORS['secondary'])
        )
        btn_back = StyledButton(
            text='Kembali',
            on_press=self.back_to_main,
            background_color=get_color_from_hex(COLORS['danger'])
        )
        button_layout.add_widget(btn_return)
        button_layout.add_widget(btn_back)
        main_layout.add_widget(button_layout)
        
        # Status Label
        self.status_label = StyledLabel(
            text='',
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(self.status_label)
        
        self.add_widget(main_layout)

    def load_active_loans(self):
        loans = self.db.get_active_loans()
        self.loan_spinner.values = [f"{id} - {title} ({name})" for id, title, name in loans]
    
    def return_book(self, instance):
        if self.loan_spinner.text == 'Pilih Peminjaman':
            self.status_label.text = 'Silakan pilih peminjaman!'
            return
        
        loan_id = int(self.loan_spinner.text.split(' - ')[0])
        success, message = self.db.return_book(loan_id)
        
        if success:
            self.load_active_loans()
            self.loan_spinner.text = 'Pilih Peminjaman'
        
        self.status_label.text = message
    
    def back_to_main(self, instance):
        self.manager.current = 'main'

class HapusAnggotaScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.db = DatabaseManager()
        
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        header = StyledLabel(
            text='Hapus Anggota',
            font_size='24sp',
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(header)
        
        # Member Selection
        self.member_spinner = StyledSpinner(
            text='Pilih Anggota',
            size_hint_y=None,
            height=40
        )
        self.load_members()
        main_layout.add_widget(self.member_spinner)
        
        # Buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=20)
        btn_delete = StyledButton(
            text='Hapus Anggota',
            on_press=self.delete_member,
            background_color=get_color_from_hex(COLORS['danger'])
        )
        btn_back = StyledButton(
            text='Kembali',
            on_press=self.back_to_main
        )
        button_layout.add_widget(btn_delete)
        button_layout.add_widget(btn_back)
        main_layout.add_widget(button_layout)
        
        # Status Label
        self.status_label = StyledLabel(
            text='',
            size_hint_y=None,
            height=40
        )
        main_layout.add_widget(self.status_label)
        
        self.add_widget(main_layout)

    def load_members(self):
        members = self.db.get_all_members()
        self.member_spinner.values = [f"{id} - {name}" for id, name in members]
    
    def delete_member(self, instance):
        if self.member_spinner.text == 'Pilih Anggota':
            self.status_label.text = 'Silakan pilih anggota!'
            return
        
        member_id = int(self.member_spinner.text.split(' - ')[0])
        success, message = self.db.delete_member(member_id)
        
        if success:
            self.load_members()
            self.member_spinner.text = 'Pilih Anggota'
        
        self.status_label.text = message
    
    def back_to_main(self, instance):
        self.manager.current = 'main'


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Header
        header = StyledLabel(
            text='Sistem Informasi Perpustakaan Digital',
            font_size='28sp',
            size_hint_y=None,
            height=100
        )
        main_layout.add_widget(header)
        
        # Menu Buttons Container
        buttons_layout = BoxLayout(orientation='vertical', spacing=20, padding=[50, 20])
        
        btn_peminjaman = StyledButton(
            text='Peminjaman Buku',
            background_color=get_color_from_hex(COLORS['primary']),
            on_press=self.ke_peminjaman
        )
        btn_hapus = StyledButton(
            text='Hapus Anggota',
            background_color=get_color_from_hex(COLORS['danger']),
            on_press=self.ke_hapus_anggota
        )
        btn_laporan = StyledButton(
            text='Generate Laporan Ke Excel',
            background_color=get_color_from_hex(COLORS['secondary']),
            on_press=self.generate_laporan
        )

        btn_pengembalian = StyledButton(
            text='Pengembalian Buku',
            background_color=get_color_from_hex(COLORS['secondary']),
            on_press=self.ke_pengembalian
        )
        
        buttons_layout.add_widget(btn_peminjaman)
        buttons_layout.add_widget(btn_pengembalian)
        buttons_layout.add_widget(btn_hapus)
        buttons_layout.add_widget(btn_laporan)
        
        main_layout.add_widget(buttons_layout)
        
        self.add_widget(main_layout)

    def ke_pengembalian(self, instance):
        self.manager.current = 'pengembalian'

    def ke_peminjaman(self, instance):
        self.manager.current = 'peminjaman'
    
    def ke_hapus_anggota(self, instance):
        self.manager.current = 'hapus_anggota'

    
    
    def generate_laporan(self, instance):
        db = DatabaseManager()
        db.cur.execute("""
            SELECT p.id_peminjaman, b.judul, a.nama, 
            p.tanggal_pinjam, p.tanggal_kembali, p.status
            FROM peminjaman p
            JOIN buku b ON p.id_buku = b.id_buku
            JOIN anggota a ON p.id_anggota = a.id_anggota
        """)
        data = db.cur.fetchall()
        columns = ['ID', 'Judul Buku', 'Nama Peminjam', 
                    'Tanggal Pinjam', 'Tanggal Kembali', 'Status']
        
        df = pd.DataFrame(data, columns=columns)
        df.to_excel(f"laporan_peminjaman_{datetime.now().strftime('%Y%m%d')}.xlsx", index=False)

class PerpustakaanApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(PeminjamanScreen(name='peminjaman'))
        sm.add_widget(HapusAnggotaScreen(name='hapus_anggota'))
        sm.add_widget(PengembalianScreen(name='pengembalian'))
        return sm

if __name__ == '__main__':
    PerpustakaanApp().run()