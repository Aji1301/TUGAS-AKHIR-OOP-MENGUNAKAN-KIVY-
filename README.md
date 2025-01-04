CREATE DATABASE perpustakaan;

CREATE TABLE buku (
          id_buku SERIAL PRIMARY KEY,
          judul VARCHAR(255) NOT NULL,
          pengarang VARCHAR (255) NOT NULL,
          penerbit VARCHAR (255) NOT NULL,
          tahun_terbit INTEGER NOT NULL,
          kategori VARCHAR (100) NOT NULL,
          stok INTEGER NOT NULL DEFAULT O
         ); 

CREATE TABLE anggota (
          id_anggota SERIAL PRIMARY KEY,
          nama VARCHAR (255) NOT NULL,
          alamat TEXT,
          no_telepon VARCHAR(15),
          tanggal_bergabung DATE DEFAULT CURRENT_DATE
        );

CREATE TABLE peminjaman (
          id_peminjaman SERIAL PRIMARY KEY,
          id_buku INTEGER REFERENCES buku (id_buku),
          tanggal_pinjam DATE DEFAULT CURRENT_DATE,
          tanggal_kembali DATE,
          status VARCHAR (50) DEFAULT 'Dipinjam',
          CONSTRAINT valid_dates CHECK (tanggal_kembali >= tanggal_pinjam)
        );
