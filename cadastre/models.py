from django.contrib.gis.db import models


class Departement(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    nom = models.CharField(max_length=100)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.nom}"


class Commune(models.Model):
    code_insee = models.CharField(max_length=5, primary_key=True)
    nom = models.CharField(max_length=200)
    code_postal = models.CharField(max_length=5)
    departement = models.ForeignKey(
        Departement, on_delete=models.CASCADE, related_name="communes"
    )

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} ({self.code_insee})"


class Parcelle(models.Model):
    idu = models.CharField(max_length=14, primary_key=True)
    geometry = models.PolygonField(spatial_index=True)
    contenance = models.IntegerField(db_index=True)
    prefixe = models.CharField(max_length=3)
    section = models.CharField(max_length=2)
    numero = models.CharField(max_length=4)
    arpente = models.BooleanField(default=False)
    commune = models.ForeignKey(
        Commune, on_delete=models.CASCADE, related_name="parcelles"
    )
    created = models.DateField(null=True, blank=True)
    updated = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["commune", "contenance"]),
        ]

    def __str__(self):
        return self.idu


class Adresse(models.Model):
    id_ban = models.CharField(max_length=50, primary_key=True)
    numero = models.CharField(max_length=10, blank=True, default="")
    rep = models.CharField(max_length=10, blank=True, default="")
    nom_voie = models.CharField(max_length=300, blank=True, default="")
    code_postal = models.CharField(max_length=5, blank=True, default="")
    code_insee = models.CharField(max_length=5, blank=True, default="")
    nom_commune = models.CharField(max_length=200, blank=True, default="")
    lon = models.FloatField(null=True, blank=True)
    lat = models.FloatField(null=True, blank=True)
    cad_parcelles = models.TextField(blank=True, default="")

    def __str__(self):
        parts = [self.numero, self.nom_voie, self.code_postal, self.nom_commune]
        return " ".join(p for p in parts if p)


class ParcelleAdresse(models.Model):
    parcelle = models.ForeignKey(
        Parcelle, on_delete=models.CASCADE, related_name="adresses_rel"
    )
    adresse = models.ForeignKey(
        Adresse, on_delete=models.CASCADE, related_name="parcelles_rel"
    )

    class Meta:
        unique_together = ["parcelle", "adresse"]

    def __str__(self):
        return f"{self.parcelle_id} <-> {self.adresse_id}"
