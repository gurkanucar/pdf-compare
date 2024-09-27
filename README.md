# pdf-compare

![./image.png](./image.png)

```bash
#mode: multiple/single

curl --location 'http://localhost:8080/compare_pdfs?mode=multiple' \
--form 'pdf1=@"/C:/Users/user/Downloads/lipsum1.pdf"' \
--form 'pdf2=@"/C:/Users/user/Downloads/lipsum2.pdf"'
```