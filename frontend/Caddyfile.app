(app_site) {
	encode gzip
	log

	handle /api* {
		request_body {
			max_size 6MB
		}
		reverse_proxy backend:8000 {
			header_up X-Forwarded-Proto {scheme}
			header_up X-Forwarded-Host {host}
			flush_interval -1
			transport http {
				read_timeout 0
				write_timeout 0
			}
		}
	}

	handle /assets/* {
		root * /usr/share/caddy
		header Cache-Control "public, max-age=31536000, immutable"
		file_server
	}

	handle {
		root * /usr/share/caddy
		header X-Content-Type-Options nosniff
		header Referrer-Policy strict-origin-when-cross-origin
		header Content-Security-Policy "frame-ancestors 'none'"
		try_files {path} /index.html
		file_server
	}
}
