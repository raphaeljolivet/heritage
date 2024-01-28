STATIC := www

default: generate

generate:
	cd ${STATIC}; python generate.py

app:
	streamlit run app.py